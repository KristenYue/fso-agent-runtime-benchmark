"""Trace and execution-boundary QA checks."""

from fso_benchmark import agent_runtime
from fso_benchmark.agent_runtime import run_agent
from fso_benchmark.langgraph_agent import run_agent as run_langgraph_agent
from fso_benchmark.planner_contract import ScriptedPlanner

from ._scenarios import happy_actions, recovery_actions


def test_rejected_tool_is_never_executed(monkeypatch) -> None:
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("tool execution must not occur")

    monkeypatch.setattr(agent_runtime, "execute_tool_action", forbidden)
    result = run_agent("select", ScriptedPlanner([{"kind": "tool", "tool": "unknown", "arguments": {}}]))
    assert result["status"] == "tool_error"
    assert calls == 0


def test_trace_contains_required_fields() -> None:
    result = run_agent("select", ScriptedPlanner(happy_actions()))
    for event in result["trace"]:
        assert {"tool", "arguments", "status"} <= event.keys()
        assert ("output" in event) ^ ("error" in event)


def test_semantic_contamination_recovers_once() -> None:
    result = run_agent("select", ScriptedPlanner(recovery_actions()), fault_profile="threshold_catalog_semantic_corruption_once")
    assert result["status"] == "success"
    assert any(event.get("recovery") == "clean_frozen_catalog" for event in result["trace"])


def test_persistent_semantic_contamination_fails_closed() -> None:
    result = run_agent("select", ScriptedPlanner(recovery_actions(persistent=True)), fault_profile="threshold_catalog_semantic_corruption_persistent")
    assert result["status"] == "tool_error"
    assert result["answer"] == {"message": "persistent corruption"}
    assert result["error"] == "persistent corruption"


def test_runtime_trajectories_match() -> None:
    custom = run_agent("select", ScriptedPlanner(happy_actions()))
    graph = run_langgraph_agent("select", ScriptedPlanner(happy_actions()))
    assert custom["trace"] == graph["trace"]
