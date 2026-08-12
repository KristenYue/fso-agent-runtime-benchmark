# 来源与仓库隔离记录

## 隔离决策

- 毕业设计工作区：`C:\Users\29007\Desktop\PythonProject\fso_thesis_simple`
- Agent Benchmark：`C:\Users\29007\Documents\AI agent\fso-agent-benchmark`
- 毕业设计工作区仅允许读取；不在其中安装依赖、生成缓存、运行会写结果的脚本、
  初始化 Git、修改或提交文件。
- Benchmark 使用独立 `.venv`、独立 `.git`、独立测试与产物目录。

## 只读来源快照

审计日期：2026-08-12。SHA-256：

| 来源 | SHA-256 | 复用内容 |
|---|---|---|
| `01_channel_model_validation.py` | `1897ED131D7429F08EE2F586DEDC408450419446DC4220C054811CAB4DB48352` | Rytov 方差到 Gamma-Gamma 参数的公式 |
| `02_uncoded_fso_ber.py` | `E6D51BC14BB5595E254D1A448F7FEAD408F0983D2C07E9E7515C2F00CA87C2EE` | 等概率 OOK/AWGN 理论 BER 公式与参数范围依据 |
| `results/08_rs_ldpc_final_summary.csv` | `933C6794139A9B7BB457CF234FE9347B77C50DD0277F77468AF1B6062FD53D92` | 16 条冻结 RS/LDPC 配置摘要 |
| `10_turbulence_sensitivity.py` | `67912C54C0811CD5D231282F176A5BBA1F29C485558058526E23A1FBD44F88C9` | 弱/中/强三档参数与敏感性实验口径 |
| `results/10_turbulence_sensitivity_summary.csv` | `6E2F0D29E1877659F6D442ABACC3B1E2BACA1F2FDFA2F27DC96A0ABCEB1C1BCF` | 12 条湍流阈值；保留 4 条未 bracket 结果为不可用 |

没有复制图片、PDF、仿真缓存、随机数状态或可写结果目录。后续若毕业设计来源发生变化，
必须显式更新哈希和数据版本；Benchmark 不自动同步，避免未提交毕业设计被隐式覆盖。
