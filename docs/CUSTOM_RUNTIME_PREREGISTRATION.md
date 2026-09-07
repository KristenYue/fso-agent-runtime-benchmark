# 自研 Agent Runtime 公平对比预注册 v1

## 状态与研究问题

本预注册在自研 Runtime 的任何 development 模型运行和 Challenge 运行之前冻结。LangGraph
正式基线对应 Git 提交 `0412f7ca19fa642b9b99f73e1789a24938de51c6`，Challenge v1 原始
结果为 24/24，结果 SHA-256 为
`9122b382b83425091ccfac151ed3f62b21c827c1e0e4d1987bdcbd351fde848d`。

研究问题是：将唯一的架构自变量从 LangGraph 1.2.11 的 StateGraph/Pregel 调度替换为本仓库
实现的显式 Python 状态机后，在模型、Prompt、工具、预算、故障和评分完全相同的条件下，
能否保持任务正确性，并降低不含模型网络等待的调度复杂度。由于 LangGraph 已达到 24/24，
本实验不声称还能提高准确率；正确性判据是同样达到 24/24 且约束违反为 0。

## 唯一架构自变量

- LangGraph 组：冻结提交中的 `StateGraph`，节点为 Planner 和 Tool；
- 自研组：`fso_benchmark.agent_runtime.run_agent` 中单线程、同步、显式 `while` 状态机；
- 自研 Runtime 不得导入 `langgraph` 或 `langchain_core`，不提供并行、持久化、人工中断或
  checkpoint；这些不属于当前冻结任务所需能力；
- 自研依赖独立锁定在 `requirements-runtime.lock`，其中不含 LangGraph/langchain-core；
- Planner HTTP 客户端、动作校验、工具实现、Planner 可见 observation、私有 context、终止
  结果契约保持相同；
- 自研运行使用独立幂等键命名空间 `fso-custom-v1`，仅避免与历史正式调用键碰撞，不改变
  请求消息、模型参数或评分。

## 冻结共同条件

- development：`data/tasks_v2.json` 中 30 条 `plan_turbulence_aware_link`；
- Challenge：`data/challenge_v1.json` 的 24 条任务，SHA-256
  `4d905a08b1b52a3be271daa53f1a9596fca16cfc5091fcfa9d2fe1a30b5f9086`；
- 模型：北京百炼 `qwen3.7-plus-2026-05-26` 固定快照，关闭思考模式；
- Planner：`planner_v1`，temperature=0，`json_object`，本地严格 Schema 校验；
- 单次模型请求超时 30 秒，429/5xx/timeout 最多重试 1 次；
- 每任务最多 8 次工具调用；恰好用满后仍允许一个 finish 动作；
- 允许工具、精确参数、目录摘要、阈值验证前置条件、成功必须引用优化器输出均不变；
- 故障 profile 对 Planner 隐藏，一次性故障允许恢复，持续故障必须停止；
- 使用同一 `matches_expected`、`score_planning_report` 和互斥失败分类，不使用
  LLM-as-judge，不人工改标签。

机器可检验哈希、模型身份和预算保存在
`artifacts/custom_runtime_contract_v1/contract.json`。

## development 与冻结规则

development 只用于发现实现错误，不允许修改 Prompt、模型、工具、预算、任务或评分器。
若发现共享契约本身必须修改，则本预注册作废并升版，且不得先查看自研 Challenge 结果。
进入 Challenge 前必须满足：

1. 自研路径在阻断 `langgraph`/`langchain_core` 导入时仍可加载；
2. 动作校验、正常成功、缺参、无可行解、预算耗尽、一次故障恢复、持续故障停止与冻结
   LangGraph 行为等价测试通过；
3. 全部仓库测试通过，development 30 条制品完整且不含凭据；
4. 当前 Prompt、Schema、数据、工具和评分器哈希与机器契约一致；
5. 当前 Runtime/Planner 源码哈希与 development manifest 完全一致；
6. 自研 Challenge 账本不存在，并由人工提供精确批准值。

Challenge 只允许最终配置运行一次。开始模型调用前写 `running` 账本；中断、provider 失败或
低分均不得删除账本后重跑。全部失败轨迹必须保留。

## 预注册指标与结论口径

主指标为严格通过数及相对 LangGraph 的差值。自研 Runtime 只有达到 24/24 且约束违反为 0，
才可称为在本冻结任务上保持正确性；23/24 或更低均不满足该判据。次指标为状态/轨迹契约、
恢复准确率、工具调用数、重复成功步骤、P50/P95 任务延迟、模型调用/尝试数、Token 和在具有
完整日期及币种价格元数据时的成本。

模型网络延迟不能证明 Runtime 本身更快。若比较调度开销，只使用相同 ScriptedPlanner 与工具
动作在同一进程、同一机器上的离线配对测量，并同时报告样本数、分布和测量脚本；该指标仅作
工程诊断，不改变主结论。

结论严格限定于这 24 条预注册任务。即使 24/24，也不得外推为开放世界可靠性或把当前仅支持
`BER=1e-3` 的配置目录外推到 `BER=1e-6`。
