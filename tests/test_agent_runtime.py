import builtins
import json
import subprocess
import sys
from pathlib import Path

import pytest

from fso_benchmark.agent_runtime import run_agent as run_custom_agent
from fso_benchmark.langgraph_agent import run_agent as run_langgraph_agent
from fso_benchmark.planner_contract import ScriptedPlanner


ROOT = Path(__file__).resolve().parents[1]


def successful_actions():
    return [
        {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_catalog","arguments":{}},
        {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Moderate","target_ber":0.001,"max_ebn0_db":25.0}},
        {"kind":"finish","status":"success","message":""},
    ]


def semantic_recovery_actions(final_status="success"):
    actions = [
        {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":2.0}},
        {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":2.0}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
    ]
    if final_status == "success":
        actions.extend(
            [
                {"kind":"tool","tool":"load_catalog","arguments":{}},
                {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Strong","target_ber":0.001,"max_ebn0_db":30.0}},
                {"kind":"finish","status":"success","message":""},
            ]
        )
    else:
        actions.append(
            {"kind":"finish","status":"tool_error","message":"persistent corruption"}
        )
    return actions


@pytest.mark.parametrize(
    "actions,fault_profile,max_tool_calls",
    [
        (successful_actions(), None, 8),
        ([{"kind":"finish","status":"needs_clarification","message":"need power"}], None, 8),
        ([{"kind":"finish","status":"success","message":""}], None, 8),
        ([{"kind":"tool","tool":"read_private_file","arguments":{}}], None, 8),
        (
            [
                {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
                {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
                {"kind":"finish","status":"tool_error","message":"stop"},
            ],
            "threshold_catalog_timeout_once",
            8,
        ),
        (
            [
                {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
                {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
                {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
            ],
            None,
            2,
        ),
        (
            semantic_recovery_actions(),
            "threshold_catalog_semantic_corruption_once",
            8,
        ),
        (
            semantic_recovery_actions("tool_error"),
            "threshold_catalog_semantic_corruption_persistent",
            8,
        ),
        (
            [
                {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
                {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
                {"kind":"tool","tool":"load_catalog","arguments":{}},
                {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Strong","target_ber":0.001,"max_ebn0_db":1.0}},
                {"kind":"finish","status":"no_feasible_solution","message":"none"},
            ],
            None,
            8,
        ),
    ],
)
def test_custom_runtime_matches_frozen_langgraph_behavior(
    actions, fault_profile, max_tool_calls
) -> None:
    custom = run_custom_agent(
        "same request",
        ScriptedPlanner(actions.copy()),
        fault_profile=fault_profile,
        max_tool_calls=max_tool_calls,
    )
    graph = run_langgraph_agent(
        "same request",
        ScriptedPlanner(actions.copy()),
        fault_profile=fault_profile,
        max_tool_calls=max_tool_calls,
    )
    assert custom == graph


def test_custom_runtime_import_does_not_require_langgraph() -> None:
    code = f"""
import builtins, sys
sys.path.insert(0, {str(ROOT / 'src')!r})
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {{'langgraph', 'langchain_core'}}:
        raise RuntimeError('forbidden framework import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import fso_benchmark.agent_runtime
print('ok')
"""
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ok"


def test_custom_runtime_exact_budget_allows_finish() -> None:
    result = run_custom_agent(
        "exact budget", ScriptedPlanner(successful_actions()), max_tool_calls=6
    )
    assert result["status"] == "success"
    assert len(result["trace"]) == 6
