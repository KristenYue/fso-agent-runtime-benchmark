import json
from pathlib import Path

from fso_benchmark.baseline import execute_direct, run_direct_baseline
from fso_benchmark.contracts import TaskSpec


ROOT = Path(__file__).resolve().parents[1]


def test_direct_baseline_matches_all_seed_ground_truth() -> None:
    cases = json.loads((ROOT / "data" / "tasks_seed.json").read_text(encoding="utf-8"))["tasks"]
    report = run_direct_baseline(cases)
    assert report["summary"]["total"] == 9
    assert report["summary"]["exact_match_rate"] == 1.0


def test_direct_executor_keeps_failure_in_trace() -> None:
    result = execute_direct(TaskSpec("bad", "L3", "calculate_ook_ber", {"ebn0_db": 101}))
    assert result.status == "invalid_input"
    assert result.answer is None
    assert result.trace[-1]["status"] == "invalid_input"


def test_unknown_operation_is_rejected() -> None:
    result = execute_direct(TaskSpec("bad-op", "L3", "delete_everything", {}))
    assert result.status == "invalid_input"


def test_multistep_matching_checks_nested_configuration_id() -> None:
    case = {
        "task_id": "nested-choice",
        "level": "L2",
        "operation": "plan_turbulence_aware_link",
        "inputs": {
            "rytov_variance": 0.75,
            "target_ber": 0.001,
            "max_ebn0_db": 25.0,
        },
        "expected": {"status": "success", "configuration_id": "wrong-choice"},
    }
    report = run_direct_baseline([case])
    assert report["results"][0]["status"] == "success"
    assert report["results"][0]["passed"] is False
