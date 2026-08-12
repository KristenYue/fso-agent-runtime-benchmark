# FSO Agent Benchmark

这是自研 Agent Runtime 的确定性工具环境与多步规划测试床。它复用原 FSO
论文仿真的物理公式和已冻结汇总结果，但不把“调用 Agent”包装成简单计算所必需。

当前已完成 P1 的非 Agent 基线，并开始多步约束环境：

- 五个无网络、无随机性的核心领域工具；
- 版本化任务契约和 150 条 L1/L2/L3 development 任务，其中30条为五步规划；
- 直接函数/确定性优化器 Oracle 基线；
- 仅读取自然语言请求的规则参数解析基线；
- 参数校验、失败结果、调用轨迹和自动化测试。

## 快速运行

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python scripts/generate_tasks_v1.py
python scripts/run_direct_baseline.py
python scripts/run_rule_baseline.py
python scripts/generate_tasks_v2.py
python scripts/run_planning_baselines_v2.py
```

完整数据集基线会写入 `artifacts/direct_baseline_v1/` 和 `artifacts/rule_baseline/`。
历史 9 条种子结果保留在 `artifacts/direct_baseline/`。100% 结果只代表确定性 Oracle 和任务契约一致，
不是 Agent 的实验成绩。后续 LangGraph 与自研 Runtime 必须在同一冻结任务集、相同工具
Schema 和相同评分器上比较。

当前规则基线覆盖受控生成模板；若达到 100%，只能证明模板可以被规则完整解析，
不能证明 Agent 有额外价值。项目在加入真正多步约束和失败恢复任务前不会冻结最终测试集。

## 确定性工具

1. `characterize_turbulence`：由 Rytov 方差计算 Gamma-Gamma 参数；
2. `calculate_ook_ber`：计算 AWGN 下等概率 OOK 理论 BER；
3. `select_configuration`：在 BER、码型、相干长度、缓存和时延约束下选择配置。
4. `resolve_turbulence_regime`：只接受已有仿真验证的 0.2/0.75/2.0 三个 Rytov 点；
5. `select_robust_configuration`：合并湍流阈值与资源目录，排除未 bracket 阈值，
   在功率和缓存约束下最小化带宽开销。

`plan_turbulence_aware_link` 的直接执行轨迹包含参数计算、湍流档位解析、两个目录读取
和约束优化五步。它是后续 Agent 规划任务的确定性 Oracle，不表示 LLM 应代替优化器。

## 数据来源边界

公式来自本地 `fso_thesis_simple` 的已验证仿真脚本；配置目录来自
`results/08_rs_ldpc_final_summary.csv`。本仓库仅保存构建任务所需的冻结子集和来源说明，
不复制论文图片、大型中间结果或随机仿真流程。

具体的只读来源哈希和仓库隔离规则见 `docs/SOURCE_PROVENANCE.md`。
