"""Fast, offline smoke checks for the public runtime boundary."""

from fso_benchmark.agent_runtime import run_agent
from fso_benchmark.langgraph_agent import run_agent as run_langgraph_agent
from fso_benchmark.planner_contract import ALLOWED_TOOLS, ScriptedPlanner

from ._scenarios import happy_actions


def test_runtime_can_start() -> None:
    result = run_agent("clarify", ScriptedPlanner([{"kind": "finish", "status": "needs_clarification", "message": "need input"}]))
    assert result["status"] == "needs_clarification"


def test_registered_tools_are_available() -> None:
    assert ALLOWED_TOOLS == {
        "characterize_turbulence", "resolve_turbulence_regime", "load_turbulence_catalog",
        "validate_turbulence_catalog", "load_catalog", "select_robust_configuration",
    }


def test_langgraph_runtime_can_start() -> None:
    result = run_langgraph_agent("clarify", ScriptedPlanner([{"kind": "finish", "status": "needs_clarification", "message": "need input"}]))
    assert result["status"] == "needs_clarification"


def test_happy_path_produces_trace() -> None:
    result = run_agent("select", ScriptedPlanner(happy_actions()))
    assert result["status"] == "success"
    assert len(result["trace"]) == 6
