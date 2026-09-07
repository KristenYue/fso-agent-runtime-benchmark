# 自研 Agent Runtime development 报告

## 结论

2026-09-07，自研 Runtime 在预注册的30条 development 规划任务上严格通过30/30，制品
完整性门禁通过，Challenge 运行数仍为0。该结果允许进入“最终配置人工确认”，不等于已经
得到自研 Runtime 的冻结 Challenge 成绩。

## 冻结配置

- Runtime：不依赖 LangGraph/langchain-core 的同步显式 Python 状态机；
- 模型：北京百炼 `qwen3.7-plus-2026-05-26` 固定快照；
- Prompt、动作 Schema、工具、评分器、8次工具预算、30秒超时和一次 provider 重试均与
  预注册契约一致；
- 独立幂等键命名空间：`fso-custom-v1`；
- development 数据 SHA-256：
  `cf9cfbfed67868ae891c89b67b97f486b7c5b109652aca93ba03d5d65d8c7e19`。

## 结果

| 指标 | 自研 Runtime | LangGraph iteration 02 |
|---|---:|---:|
| 严格通过 | 30/30 | 30/30 |
| 成功规划 | 18/18 | 18/18 |
| 缺参澄清 | 6/6 | 6/6 |
| 首次 timeout 恢复 | 3/3 | 3/3 |
| 持续故障正确停止 | 3/3 | 3/3 |
| 约束违反 | 0 | 0 |
| 过早停止 | 0 | 0 |
| 非必要重复成功步骤 | 0 | 0 |
| 模型调用 / provider 尝试 | 162 / 162 | 162 / 162 |
| Prompt tokens | 228,848 | 228,848 |
| Completion tokens | 6,847 | 6,934 |
| Total tokens | 235,695 | 235,782 |
| P50 任务延迟 | 9,199.36 ms | 8,480.04 ms |
| P95 任务延迟 | 11,369.29 ms | 9,731.66 ms |

两次 development 的任务结果、工具调用数和恢复指标相同。Completion tokens 相差87，说明
即使 temperature=0，独立服务商调用也不应被解释为逐 token 完全确定。

自研运行的端到端延迟更高，但该数字由不同时间发生的模型网络请求主导，不能据此判断 Python
状态机调度比 LangGraph 更慢。预注册已规定：Runtime 调度开销若需比较，必须另做同机、同进程、
相同 ScriptedPlanner 的离线配对测量，且只作工程诊断。

## 制品验收

- `artifacts/custom_runtime_development/results.json` SHA-256：
  `8aac5eb261c3e2cca39f73b50b90b87a2d76dc3a54aaa0777f1435a47f3e56e5`；
- `artifacts/custom_runtime_development/manifest.json` SHA-256：
  `d15f0c46718f00b3fa223565371ab39d8bfd1316b1ebee3df8491443cc845232`；
- 30个预注册 task ID 完整且无重复；汇总、逐任务结果、遥测和失败分类相互一致；
- 预注册契约及全部共同组件哈希匹配；Runtime/Planner 源码哈希已写入 manifest；
- provider 尝试无重试，usage 完整；API Key 未写入 manifest、结果或仓库；
- 未提供带日期、币种的完整价格元数据，因此不报告成本；
- 自研 Challenge 账本不存在，Challenge 任务运行数为0。

## 下一道闸门

在不再修改 Runtime/Planner、Prompt、Schema、工具、预算和评分器的前提下，由人工明确批准
唯一一次自研 Challenge 正式运行。运行器会在首个模型调用前写入 `running` 账本；无论结果、
中断或服务商错误如何，都不得删除账本后重跑。
