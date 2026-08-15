# LangGraph 基线结果分析口径

## 目的

development 与冻结 Challenge 使用同一个确定性评分器。模型输出后不人工改标签，不删除
失败轨迹，不用 LLM-as-judge 替代可执行 ground truth。`passed` 仍由冻结的
`matches_expected` 决定；本文件只规定次级诊断指标和失败归因。

## 互斥失败分类

每条任务只进入一个类别，按以下优先级判定：

1. `passed`：状态、答案和必要轨迹全部符合契约；
2. `invalid_planner_action`：模型动作未通过本地 Schema/白名单校验；
3. `tool_budget_exhausted`：模型仍请求工具但 8 次工具预算已耗尽；
4. `provider_error`：timeout、HTTP 错误或服务商响应协议错误；
5. `premature_stop`：预期成功但 Agent 以非成功状态结束；
6. `wrong_status`：实际终止状态与预期不同；
7. `recovery_contract_failed`：任务要求恢复，但轨迹没有恢复标记；
8. `trace_contract_failed`：缺少要求出现的错误/验证状态；
9. `wrong_configuration`：成功状态正确，但最终配置 ID 错误；
10. `answer_contract_mismatch`：其余可执行答案契约不匹配。

分类依据只来自任务契约、结果和轨迹。隐藏 `injected_fault` 只供评分器解释环境，不进入
Planner 上下文。

## 自动报告指标

- 严格任务通过率；
- 约束违反数/率与平均 optimality gap；
- 平均工具调用数；
- 首次 timeout 恢复率；
- 一次性语义污染恢复率；
- 持续语义污染正确停止率；
- 缺参澄清准确率；
- 过早停止数；
- 非必要的重复成功步骤；
- 每类失败数量；
- P50/P95 任务延迟、模型调用/尝试次数、Token 与有来源价格时的成本。

语义恢复所需的第二次目录读取不计作“非必要重复”。持续污染任务只有按契约停止并返回
`tool_error` 才计为正确停止。网络/服务商错误使用独立异常进入 `provider_error`，不得包装成
`invalid_planner_action`。

## 制品门禁

development 验收要求 30 条规划任务完整覆盖，并要求 `planning_metrics` 与
`failure_analysis` 存在、失败数与逐任务 `passed` 一致、类别计数覆盖全部任务。该门禁验证
制品完整性，不把某个最低通过率偷偷改成 Challenge 前的调参信号。
