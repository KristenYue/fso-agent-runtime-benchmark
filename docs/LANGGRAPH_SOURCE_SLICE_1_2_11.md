# LangGraph 1.2.11 源码切片：图执行与 checkpoint

## 范围与证据

本切片只回答后续自研 Runtime 必须理解的两个问题：图怎样从声明变成执行，以及状态怎样
持久化。证据来自独立虚拟环境内安装的 `langgraph==1.2.11`、
`langchain-core==1.5.4` 和 `langgraph-checkpoint==4.2.0`。版本、锁文件和五个源码文件的
SHA-256 记录在 `artifacts/langgraph_source_slice_v1/manifest.json`。wheel 元数据没有上游
Git SHA，因此不虚构提交映射，以精确版本和本地源码哈希作为可复验标识。

## 最小调用链

```text
StateGraph(state_schema)
  -> add_node / add_edge / add_conditional_edges
  -> compile(checkpointer=...)
  -> CompiledStateGraph(Pregel)
  -> invoke(...)
  -> stream(...)
  -> SyncPregelLoop + PregelRunner
  -> loop.tick() -> runner.tick(tasks) -> loop.after_tick()
  -> apply channel writes -> checkpoint -> next superstep / END
```

1. `graph/state.py:131`：`StateGraph` 是构建器，节点签名是
   `State -> Partial<State>`；同一 state key 的并发更新由 reducer 合并。
2. `graph/state.py:1177`：`compile()` 先校验 schema、节点、边和 interrupt，再创建
   `CompiledStateGraph`；后者继承 `Pregel`。约在 1373—1399 行把 START、节点、边和条件
   分支附加到可执行对象。
3. `pregel/main.py:3836`：`invoke()` 不是另一套执行器，而是消费 `stream()` 并整理最终值、
   更新或 interrupt。
4. `pregel/main.py:2899`：同步 `stream()` 创建 `SyncPregelLoop` 和 `PregelRunner`。
   2964—2984 行的主循环先准备本轮任务，再执行任务并提交 writes，最后 `after_tick()`。
   第 N 步产生的 channel 更新只在第 N+1 步可见，这是明确的 Bulk Synchronous Parallel
   边界，而不是节点随意原地修改共享对象。
5. `pregel/_loop.py:599`：`tick()` 从 checkpoint、pending writes、channels 和触发关系生成
   下一批任务；无任务、interrupt、drain 和 recursion limit 都有独立终止语义。
   `after_tick()` 原子地应用 writes、发出 values、清理 pending writes 并保存 checkpoint。
6. `pregel/_runner.py:135`：Runner 负责单步内任务执行、并发、retry、异常传播和 writes
   commit；Loop 负责跨步状态与持久化，两者职责分开。
7. `checkpoint/base/__init__.py:176`：持久化抽象以 `thread_id` 定位执行历史，核心接口是
   `get_tuple`、`list`、`put` 和 `put_writes`。checkpoint 保存状态版本，pending writes
   支持恢复时避免重做已经成功的同批任务。

## 对当前 FSO Agent 的解释

`src/fso_benchmark/langgraph_agent.py` 已使用 TypedDict state、Planner/Tool 两节点和条件路由，
但目前是单次、无 checkpointer 的模型基线。`observations` 是给 Planner 的可见事实，完整目录和
故障 profile 留在 runtime context；这是“可见状态”和“运行环境”边界，不应混为一个 Prompt。
当前最多 8 次工具调用是业务预算，LangGraph 的 recursion limit 只是执行器保险，两者不能互相
替代。

## 后续 Runtime 借鉴什么

- 保留“声明/注册”和“执行实例”分离：Tool Registry 与 Agent Loop 不应是同一个对象；
- 节点返回显式更新，统一由循环提交；trace、预算和 checkpoint 才能观察同一事实；
- 明确 step 边界和终止状态，失败、interrupt、预算耗尽不能都压成普通异常；
- checkpoint 同时保存状态版本与待提交 writes，恢复必须考虑已经成功的副作用；
- 同步路径先完整实现，再让异步路径共享协议与测试，不维护两套语义。

## 不直接照搬什么

- 不为当前单 Agent FSO 场景复制 channel、subgraph、多 stream mode 和通用并发调度全套抽象；
- 不依赖隐式全局 config 传递权限、预算或用户身份，这些应是自研 Runtime 的显式输入；
- 不把 recursion limit 当 loop detection，也不把框架 retry 当工具幂等保证；
- 在真实 LangGraph 模型基线完成前，不据此开始 Runtime 实现或宣称优于 LangGraph。

## 对抗性检查

只看 `StateGraph` API 容易误以为 LangGraph 是简单节点路由；源码显示复杂度主要位于
superstep、pending writes、恢复与并发提交。反过来，直接复刻这些内部结构也不合理：本项目
首先要证明最小 ReAct/tool loop 的确定性控制和恢复价值，再由故障实验决定需要多少持久化与
并发能力。
