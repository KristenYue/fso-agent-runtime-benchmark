# ADR 0003：故障注入属于工具环境，不属于 Planner 输入

## Context

Challenge v1 包含首次超时、持续不可用和语义污染任务。直接 Oracle 已支持这些故障，
但早期 LangGraph 工具节点总是读取干净目录，使 Agent 无法观察或恢复同一故障。

## Decision

- 测试运行器从任务夹具读取 `injected_fault`，只把它传给工具环境；
- Planner 只接收自然语言请求和真实工具 observation；
- transient fault 按调用次数变化，persistent fault 每次重复；
- 语义验证失败使用 `semantic_error`，恢复成功写 `clean_frozen_catalog`；
- 达到工具调用上限后仍允许 Planner 输出最终 finish，但禁止新增工具调用。

## Alternatives

- 把故障 profile 写进 Planner Prompt：泄露隐藏测试条件；拒绝。
- 只在自然语言中描述故障、不改变工具行为：无法验证检测与恢复；拒绝。
- 由模型自行声称重试成功：轨迹不可执行；拒绝。

## Evidence

端到端 MockTransport 测试执行9次 Planner 决策和8次工具调用，完成一次语义污染恢复；
所有模型请求均不含 profile 名称，轨迹包含 `semantic_error` 和恢复标记。当前67项测试通过。

## Consequences

Runner 知道测试环境故障，但 Agent 不知道隐藏配置，这是标准评测环境与被测策略的边界。
新增故障类型必须同时实现确定性触发、可观察症状、恢复/停止条件和测试。

## Adversarial review

可能质疑 Runner 读取隐藏字段违反公平性。隐藏字段只配置环境行为，不参与 Planner 参数
解析或答案选择；所有配置使用相同 Runner，且 Agent 只能从工具响应获知故障。
