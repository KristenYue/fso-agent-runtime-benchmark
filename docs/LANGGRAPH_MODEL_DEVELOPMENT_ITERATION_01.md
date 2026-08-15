# LangGraph 模型 Development 第一次迭代报告

日期：2026-08-16

## 配置与边界

- 模型：北京百炼 `qwen3.7-plus-2026-05-26` 固定快照；
- 模式：`json_object`，关闭 thinking，本地动作校验；
- 数据：`tasks_v2.json` 中全部 30 条五步规划 development 任务；
- Challenge 调用：0；
- 原始制品：`artifacts/langgraph_model_development_runs/iteration_01/`；
- 凭据记录：否。

## 结果

- 通过：9/30（30%）；
- 成功规划：0；
- 缺参澄清：6/6；
- 持续目录故障正确停止：3/3；
- 过早停止：18；
- 首次超时恢复：0/3；
- 失败分类：10 条 `premature_stop`、8 条 `tool_budget_exhausted`、3 条 `wrong_status`；
- 模型调用：209 次，无 provider 重试；
- Token：输入 136648、输出 9662、合计 146310；
- 按 2026-08-16 北京地域原价计算成本：CNY 0.350592；
- 任务延迟：P50 约 12.78 秒，P95 约 17.46 秒。

## 根因与允许的 development 调整

冻结 Prompt 要求模型使用精确工具参数名，但 Prompt 和动作 Schema 都没有提供每个工具的
参数契约。模型能完成目录加载与校验，却把原始 `rytov_variance` 直接传给
`select_robust_configuration`，并交替尝试 `rytov`；该工具实际要求先把 Rytov 方差解析成
`turbulence`，同时使用 `max_ebn0_db`。部分轨迹还给无参目录工具增加了 `catalog` 参数，
耗尽了 8 次工具预算。

因此本轮结果不能被解释为模型 Agent 的最终能力。下一轮只做接口契约层面的修正：在
Prompt/Schema 中显式列出精确工具签名、标准调用顺序、一次恢复策略和终止状态映射；不修改
development 数据、Oracle、评分器或 Challenge。修改后重新冻结并绑定同一模型快照，先做
一次兼容性探测，再重跑 30 条 development。
