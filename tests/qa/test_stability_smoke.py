"""Small CI-safe repeatability check; the 5,000-run soak is separately scheduled."""

from fso_benchmark.agent_runtime import run_agent
from fso_benchmark.planner_contract import ScriptedPlanner

from ._scenarios import happy_actions, recovery_actions


def test_four_deterministic_scenarios_remain_stable_for_50_cycles() -> None:
    scenarios = [
        (happy_actions, None, "success"),
        (lambda: [{"kind": "finish", "status": "needs_clarification", "message": "need input"}], None, "needs_clarification"),
        (recovery_actions, "threshold_catalog_semantic_corruption_once", "success"),
        (lambda: recovery_actions(persistent=True), "threshold_catalog_semantic_corruption_persistent", "tool_error"),
    ]
    signatures = {}
    for _ in range(50):
        for factory, profile, expected in scenarios:
            result = run_agent("offline QA", ScriptedPlanner(factory()), fault_profile=profile)
            signature = (result["status"], tuple((item["tool"], item["status"]) for item in result["trace"]))
            assert result["status"] == expected
            assert signatures.setdefault((expected, profile), signature) == signature
