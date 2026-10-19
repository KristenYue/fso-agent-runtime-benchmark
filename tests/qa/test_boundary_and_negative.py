"""Parameterized malformed-action checks at the planner contract boundary."""

import pytest

from fso_benchmark.agent_runtime import run_agent
from fso_benchmark.planner_contract import ScriptedPlanner


@pytest.mark.parametrize(
    "bad_action",
    [
        {},
        {"kind": "tool", "tool": "", "arguments": {}},
        {"kind": "tool", "tool": "unknown", "arguments": {}},
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": None},
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {}},
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": "wrong"}},
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 11}},
        {"kind": "tool", "tool": "load_catalog", "arguments": {"extra": True}},
        {"kind": "finish", "status": "unknown", "message": "bad"},
        "not-json-object",
    ],
)
def test_invalid_actions_are_rejected(bad_action) -> None:
    result = run_agent("select", ScriptedPlanner([bad_action]))
    assert result["status"] == "tool_error"
    # Contract-invalid actions fail before execution; schema-valid values outside
    # a tool's domain deliberately leave one structured error observation.
    if result["trace"]:
        assert len(result["trace"]) == 1
        assert result["trace"][0]["status"] == "error"
    else:
        assert result["trace"] == []
