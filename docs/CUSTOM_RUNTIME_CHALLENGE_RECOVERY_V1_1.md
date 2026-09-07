# 自研 Runtime Challenge v1.1 事故恢复协议

## 定位

本协议不是删除或重跑原始 v1 账本。v1 原始0/24、0次模型调用和事故报告永久保留。v1.1 是在
事故完全披露后单独批准的恢复运行，继续使用同一24条任务，因此证据强度低于一次未中断的原始
预注册实验，最终报告必须同时呈现 v1 事故与 v1.1 结果。

## 不变项

模型快照、Prompt、动作 Schema、Runtime/Planner 四个源码哈希、工具、目录、故障 profile、
评分器、8次工具预算、30秒请求超时和一次 provider 重试均与原预注册及 development 完全一致。
新幂等键命名空间为 `fso-custom-v1-1`，只用于避免历史调用键碰撞。

机器可验证契约位于
`artifacts/custom_runtime_recovery_contract_v1_1/contract.json`，其中绑定原事故 ledger/results、
原比较契约、development manifest、Challenge 数据和 Runtime 源码哈希。

## 新增的账本前门禁

新正式账本创建前必须依次满足：

1. API Key 非空、只含 ASCII 且不含任何空白；
2. 不读取 Challenge 的固定缺参请求完成一次真实 provider 探测；
3. 探测必须只有1次 provider 尝试、HTTP 200、结构化动作合法，并返回
   `finish/needs_clarification`；
4. 探测制品必须绑定本恢复契约哈希、固定模型身份，且声明 Challenge 运行数为0；
5. 原事故、原比较契约、development、Challenge 和 Runtime 源码的全部哈希匹配；
6. v1.1 新账本不存在；
7. 人工已明确要求重新进行一次恢复运行。

任一项失败都必须在创建新账本前停止并询问用户，不允许自动继续 Challenge。

## 正式运行规则

全部前门禁通过后，先在 `artifacts/custom_runtime_challenge_v1_1/` 写入状态为 `running` 的新账本，
再读取24条 Challenge 并调用模型。v1.1 只允许一个账本和一次正式执行；开始后发生的模型、网络、
工具或评分失败均原样保留，不再自动补跑。
