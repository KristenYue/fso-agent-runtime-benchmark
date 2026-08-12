# FSO 任务数据卡

## 用途

本数据用于评测 Agent 是否能在确定性 FSO 工具环境中完成参数计算、约束过滤、
多步选择以及对无效请求的拒绝。它不用于训练通信模型，也不证明 Agent 优于直接计算。

## 来源

- 信道公式：本地 `fso_thesis_simple/01_channel_model_validation.py`；
- OOK BER 公式：本地 `fso_thesis_simple/02_uncoded_fso_ber.py`；
- 配置记录：本地 `fso_thesis_simple/results/08_rs_ldpc_final_summary.csv`；
- 原仿真固定种子为 20260619--20260622；本仓库当前工具本身无随机性。

## 当前参数空间

- Rytov 方差：`0 < sigma_R^2 <= 10`；
- Eb/N0：`-20 <= dB <= 100`；
- 目标 BER：`0 < BER < 0.5`；
- 编码：RS、LDPC；相干长度：64、256 bit；交织深度：1、8、32、128；
- 可选约束：最大缓存 KiB、最大额外时延 us、允许码型。

## 难度

- L1：单工具、字段完整；
- L2：至少一次约束过滤和选择；
- L3：缺字段、冲突约束、越界值或无可行解，期望显式失败。

当前包含 120 条 development 任务：train/dev/test 各 40 条，每个 split 的
L1/L2/L3 分布为 16/16/8。模板 ID 按 split 隔离，语义重复项按
`operation + canonical inputs` 去重。这里的 `test` 只验证隔离机制，尚不是最终冻结
测试集；真正多步约束和工具失败恢复任务加入后才会冻结哈希。

development v1 数据 SHA-256 为
`bdd8a3a234151cde9356333ad8a4cb0367c28ebb70647f347b708204f2fa0295`。
规则解析基线在这批受控模板上达到 100%，说明当前语言变化仍不足以构成 Agent 任务。

## 地面真值与局限

答案由确定性工具程序生成。配置的 `required_ebn0_db` 是既有有限样本仿真的冻结结果，
不是解析定理；其中 RS 置信区间字段缺失，当前优化器不把未知置信区间当作零不确定性。
当前目录只覆盖 BER、缓存和时延代理，不覆盖天气、链路距离、硬件功耗和真实部署成本。
