# LangGraph 模型基线预注册草案

## 当前状态

LangGraph 图执行骨架可以在无模型、无网络模式下验证 State 和节点连线，但该离线图仍使用
冻结规则解析器，不能称为 Agent 基线，也不会在 Challenge v1 上重复运行。

正式模型基线开始前必须补全并冻结：

- LangGraph 精确版本；
- 模型提供方和不可变快照 ID；
- temperature、结构化输出 Schema、Prompt 哈希；
- 最大步数、总 Token 预算、单次和任务总超时；
- 仅一次工具重试、停止条件和允许工具清单；
- development 上选择最终配置的规则；
- Challenge v1 仅运行最终配置一次。

## 指标

- 主指标：Challenge v1 严格任务通过率；
- 次指标：约束违反率、工具调用数、重复步骤、过早停止、恢复准确率、P50/P95、Token
  和调用成本；
- 推翻条件：未高于规则基线4/24，或通过率提升伴随任何危险约束违反。

## 当前阻塞

截至2026-08-12，独立仓库环境没有配置 DASHSCOPE/OpenAI/Qwen API Key。没有真实模型调用
和原始轨迹前，不报告 LangGraph Agent 数字。

当前离线环境固定为 LangGraph 1.2.11、langchain-core 1.5.4；完整依赖见
`requirements-agents.lock`。离线 StateGraph 只在30条 development 规划任务上运行，
Challenge v1 运行数为0。

模型无关循环已固定为 Planner→Tool→Planner，最多8次工具调用。工具白名单、阈值目录
语义验证和“成功必须引用优化器输出”由运行时执行，不依赖 Prompt 自律。Prompt 与动作
Schema 的哈希由 `scripts/freeze_langgraph_model_contract.py` 保存；故障 profile 仅配置工具环境，
不会进入 Planner 上下文，目录 observation 只暴露摘要。Challenge 运行器还会要求当前冻结
契约哈希与 development manifest 完全一致；模型提供方和快照仍待配置。真实调用前必须先用
`scripts/bind_langgraph_model_contract.py` 将 provider、OpenAI-compatible base URL 和不可变
snapshot ID 写入契约；API Key 不写入任何文件。绑定后的身份不得通过同一脚本改写，且
development 已存在时禁止绑定或重绑。

development 运行结束后先执行：

```powershell
python scripts/assess_langgraph_model_development.py
```

只有数据/契约哈希、30条规划任务覆盖、汇总、逐调用遥测和凭据排除检查全部通过，才允许
人工确认最终配置。该检查只证明制品完整，不代表模型效果达标，也不读取 Challenge。
