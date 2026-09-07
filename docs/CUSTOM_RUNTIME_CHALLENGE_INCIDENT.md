# 自研 Runtime Challenge v1 基础设施事故记录

## 结论

2026-09-07 的自研 Runtime Challenge v1 已按原协议建立并完成账本，但没有产生有效 Agent
评测：24条记录全部在本地构造 HTTP Authorization header 时失败，模型调用和 provider 尝试均
为0，工具轨迹均为空。因此原始0/24必须保留，但不得解释为模型或 Runtime 的任务通过率，也不
能与 LangGraph 24/24进行能力比较。

原协议规定账本一旦建立不得自动重跑。当前没有删除账本、修改原始结果或进行第二次调用。

## 事实链

- 原始结果 SHA-256：
  `bed2bcae704dcb8bf7d7b26555a498e8ab5148eab2ff47e30ac30bade8499ac7`；
- 原始账本 SHA-256：
  `2bee871154c84edb2aee3b6d16cbf9088bace7d69bf7e4c8177875fd038797bb`；
- 24条记录只有一个相同错误：Authorization header 的 ASCII 编码失败；
- 模型调用数0、provider 尝试数0、Token 0；
- 24条 trace 全为空，没有任何 Planner action 或工具执行；
- 本地最小复现确认：包含四个非 ASCII 字符的 `Bearer` header 会产生完全相同的错误位置，
  纯 ASCII 测试值可以正常构造；
- API Key 原文未记录，运行结束后已从进程环境清除。

## 根因与遗漏门禁

遮罩输入框只检查了“非空”，没有在建立一次性账本前检查 API Key 是否为可编码的 ASCII
凭据。HTTP 客户端在进入网络 transport 前抛出 `UnicodeEncodeError`。由于该异常继承自
`ValueError`，Runtime 的通用动作校验分支又将其标成了 `invalid_planner_action`；这是次级错误
归因问题，不代表模型返回了非法动作。

development 使用有效 ASCII 密钥，因此没有暴露这一输入边界。最终预检验证了模型 payload，
但 MockTransport 测试使用的是 ASCII 测试密钥，也没有覆盖非 ASCII credential fail-fast。

## 结果口径

必须同时保留两层口径：

1. 协议/账本事实：Challenge v1 已被消费，原始结果是0/24；
2. 科学解释：这是0次 provider 调用的本地认证基础设施事故，没有形成 Agent 能力观测，不能
   纳入 LangGraph 与自研 Runtime 的效果差值。

事后分析保存在
`artifacts/custom_runtime_challenge/posthoc_incident_analysis_2026-09-07.json`，它不覆盖原始
results 或 ledger。

## 后续决策边界

不得静默删除账本并重跑 v1。若仍需获得有效正式对比，只能显式建立新的协议版本，至少应：

- 原样引用并保留本事故的账本、结果和哈希；
- 在读取 Challenge 数据和建立正式账本前验证凭据非空、ASCII 可编码，并完成一次不含
  Challenge 的 provider 鉴权探测；
- 将认证/transport 错误与模型动作 Schema 错误分开；
- 明确说明新版本使用相同24条任务，因此属于透明的事故后补跑，证据强度低于原始盲式一次性
  设计；
- 获得新的人工明确批准后，才允许产生一次新的正式账本。
