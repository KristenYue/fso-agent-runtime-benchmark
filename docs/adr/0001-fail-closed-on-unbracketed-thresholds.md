# ADR 0001：未 bracket 的 BER 阈值不得作为可行配置

## Context

湍流敏感性汇总有 12 条记录，其中弱/强湍流下的 4 条 RS 曲线没有 bracket
`BER=1e-3`。CSV 提供了 pessimistic bound，但没有可确认的 crossing。

## Decision

多步优化器只接受 `target_bracketed=true` 且 `required_ebn0_db` 非空的记录。
未 bracket 记录计入 `unavailable_threshold_count`，但不参与可行集。若剩余配置都违反
功率、缓存或码型约束，返回 `no_feasible_solution`，不使用 bound 猜测答案。

## Alternatives

- 把 pessimistic bound 当作阈值：会把统计上未确认的结果伪装成 ground truth；拒绝。
- 对缺失阈值做线性外推：超出已有扫频范围且没有验证；拒绝。
- 删除这些记录：会掩盖工具数据不足这一真实失败模式；拒绝。

## Evidence

- `results/10_turbulence_sensitivity_summary.csv` 的冻结 SHA-256 已记录在来源文档；
- 单元测试验证强湍流、RS-only 请求返回无可行解并报告 2 条不可用阈值；
- 全量测试：25 passed。

## Consequences

可行率会低于使用外推的方案，但 ground truth 更可审计。未来若毕业设计补充更宽 Eb/N0
扫频，必须更新来源哈希和数据版本后才能启用新阈值。

## Adversarial review

常见质疑是“pessimistic bound 已经足够保守，为什么不用”。原因是 bound 只描述当前
采样区间的不确定性，不证明目标 crossing 已发生；把它当阈值会混淆上界和估计值。
