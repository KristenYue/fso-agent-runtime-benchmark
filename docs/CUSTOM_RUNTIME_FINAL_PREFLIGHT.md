# 自研 Agent Runtime 最终配置预检

## 结论

自研 Runtime 已完成预注册要求的最后两项非 Challenge 验证。119项代码测试通过；development
manifest 中记录的四个 Runtime/Planner 源码哈希与当前文件完全一致；自研 Challenge 账本仍不
存在。当前配置可以提交人工确认，预检过程没有读取或运行 Challenge 任务。

## 模型请求等价性

新增 MockTransport 契约测试，在相同 request、observations、step、模型、Prompt、Schema、
temperature、response format、思考模式、超时和重试预算下分别构造两组请求。序列化后的 HTTP
JSON payload 完全相等；唯一差异是预注册允许的幂等键命名空间：历史 LangGraph 使用 `fso-*`，
自研 Runtime 使用 `fso-custom-v1-*`，用于避免正式运行之间的 provider 幂等缓存碰撞。

该测试不调用网络、不消耗 Token，也没有修改 Runtime/Planner 源码。

## 离线调度开销

测量脚本：`scripts/benchmark_runtime_overhead.py`。

方法：同一 Python 进程、同一机器、相同 ScriptedPlanner、相同自然语言 request、相同6次
确定性工具调用和最终 finish；先执行25组预热，再执行500组配对测量。每组内执行顺序交替，
使用 `time.perf_counter_ns` 计时，不调用模型或网络。冻结 LangGraph 路径保持正式基线实际行为，
即每个任务调用 `run_agent` 时构建并编译 StateGraph。

| 指标 | LangGraph | 自研 Runtime |
|---|---:|---:|
| Mean | 6,356.06 μs | 306.68 μs |
| Median | 6,209.75 μs | 294.80 μs |
| P95 | 7,216.40 μs | 421.50 μs |
| 标准差 | 1,434.29 μs | 65.90 μs |

- 中位数比值：LangGraph / 自研 Runtime = 21.06×；
- 配对中位差（自研 − LangGraph）：−5,898.00 μs；
- 500/500组中自研 Runtime 耗时更低；
- 原始测量制品 SHA-256：
  `93f1d5c9ad5ef910b9291165a75ef9ea535efc5521757baf176a9c2115a6df5e`。

该结果证明当前实现的本地调度路径更轻，但绝对中位差只有约5.9 ms。自研 development 的真实
单任务 P50 为约9.20秒，因此这部分节省只相当于约0.064%的端到端时间，模型网络等待仍占主导。
不得把21.06×表述为真实 Agent 端到端加速21倍。

## 最终闸门状态

- Prompt、Schema、数据、工具和评分器哈希：匹配；
- development：30/30且制品验收通过；
- Runtime/Planner 源码：与 development manifest 匹配；
- 请求 payload：除幂等键前缀外相同；
- 完整代码测试：119项通过；
- 自研 Challenge 账本：不存在，正式运行数为0；
- 剩余条件：人工明确批准唯一一次正式运行并在遮罩输入框提供本次 API Key。
