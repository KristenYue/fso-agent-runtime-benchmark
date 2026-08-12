# LangGraph 离线图执行 Smoke

## 结果

- LangGraph：1.2.11；langchain-core：1.5.4；
- development 规划任务：30/30；
- Challenge v1 运行数：0；
- 模型和网络调用：0；
- 源码：`4e5bf09b995b49b4e8ad6793fcdfc782f89e7bc2`；
- 依赖锁 SHA-256：`be95385ea1d2f4c735ac4b49e6c60a9d1875216c59392233b47ff99fc188dd60`。

## 准确口径

该 smoke 只证明 StateGraph 的 State、节点、边和确定性工具执行可以编译并运行。解析节点
仍调用冻结规则解析器，所以30/30与既有规则 development 基线等价，不是模型 Agent
成绩，也不能与 Challenge v1 的规则4/24直接包装成改进。

正式 LangGraph Agent 仍需真实模型凭据、Function Calling/结构化输出、固定 Prompt 和
development 配置选择。满足这些条件后，Challenge v1 只运行最终配置一次。
