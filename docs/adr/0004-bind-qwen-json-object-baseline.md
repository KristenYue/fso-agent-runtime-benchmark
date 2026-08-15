# ADR 0004：百炼基线使用固定 Qwen 快照与 JSON Object

## Context

截至 2026-08-16，阿里云百炼官方模型目录标明 `qwen3.7-plus-2026-05-26` 支持结构化输出
和 Function Calling，且它是固定快照。北京地域 OpenAI-compatible Base URL 使用业务空间
专属域名。Chat Completions 参数文档只列出 `response_format.type=json_object`，没有承诺
OpenAI `json_schema` 请求格式。

## Decision

- provider：`AlibabaCloud-ModelStudio-Beijing`；
- snapshot：`qwen3.7-plus-2026-05-26`；
- endpoint：用户专用北京 Workspace 的 `/compatible-mode/v1`；
- provider response format：`json_object`；
- thinking：显式关闭；
- temperature：0；
- 无论 provider 是否承诺格式，所有动作仍经过本地 Schema、字段集合和工具白名单校验。

模型身份契约必须同时冻结 response format、thinking mode 与本地校验要求。development 和
Challenge 从契约读取这些值，不允许用环境变量静默切换。

## Evidence

- 模型能力：https://help.aliyun.com/zh/model-studio/qwen3-7-plus
- Chat Completions 参数：https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions
- Base URL：https://help.aliyun.com/zh/model-studio/base-url
- 2026-08-16 查询价格：北京地域输入 2 元/百万 Token，输出 8 元/百万 Token（输入不超过
  256K）；实际账单和优惠以后续运行时控制台为准。

## Consequences

选择 `json_object` 会弱化服务端 Schema 保证，但不会弱化系统边界，因为本地验证在任何工具
执行之前运行。若模型返回格式正确但动作不合法，任务记为 `invalid_planner_action`，不得自动
放宽 Schema。未来比较其他模型时必须使用同一 Prompt、工具、预算和本地验证。

## Adversarial review

不能因为百炼宣称“结构化输出”就假设它接受 OpenAI `json_schema`。反过来，也不能把本地
校验后的 JSON Object 与完全无约束文本输出混为一谈：provider 负责生成合法 JSON，本地
runtime 负责执行安全与动作契约。
