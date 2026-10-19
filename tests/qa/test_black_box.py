"""Input/output QA checks without relying on internal runtime state."""

from fso_benchmark.agent_runtime import run_agent
from fso_benchmark.planner_contract import ScriptedPlanner

from ._scenarios import happy_actions


def test_valid_task_completes() -> None:
    assert run_agent("select", ScriptedPlanner(happy_actions()))["status"] == "success"


def test_missing_parameter_requests_clarification() -> None:
    result = run_agent("select", ScriptedPlanner([{"kind": "finish", "status": "needs_clarification", "message": "need target BER"}]))
    assert result["status"] == "needs_clarification"
    assert result["trace"] == []


def test_unknown_tool_is_rejected() -> None:
    result = run_agent("select", ScriptedPlanner([{"kind": "tool", "tool": "delete_database", "arguments": {}}]))
    assert result["status"] == "tool_error"
    assert "not allowed" in result["error"]


def test_budget_exhaustion_stops_safely() -> None:
    repeated = [{"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 0.75}}] * 9
    result = run_agent("select", ScriptedPlanner(repeated), max_tool_calls=8)
    assert result["status"] == "tool_error"
    assert result["error"] == "tool-call budget exhausted"
    assert len(result["trace"]) == 8


def test_repeated_deterministic_input_has_same_terminal_state() -> None:
    first = run_agent("select", ScriptedPlanner(happy_actions()))
    second = run_agent("select", ScriptedPlanner(happy_actions()))
    assert (first["status"], first["trace"]) == (second["status"], second["trace"])
