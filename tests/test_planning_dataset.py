import json
from pathlib import Path

from scripts.generate_tasks_v2 import generate

from fso_benchmark.planning_metrics import (
    run_planning_baseline,
    run_rule_planning_baseline,
)
from fso_benchmark.rule_parser import parse_request


ROOT = Path(__file__).resolve().parents[1]


def planning_cases():
    return [
        case for case in generate()["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]


def test_v2_has_150_tasks_and_30_planning_cases() -> None:
    payload = generate()
    assert len(payload["tasks"]) == 150
    cases = planning_cases()
    assert len(cases) == 30
    assert all(sum(case["split"] == split for case in cases) == 10 for split in ("train", "dev", "test"))


def test_checked_in_v2_dataset_matches_generator() -> None:
    checked_in = json.loads((ROOT / "data" / "tasks_v2.json").read_text(encoding="utf-8"))
    assert checked_in == generate()


def test_rule_parser_reads_planning_requests_without_hidden_inputs() -> None:
    for case in planning_cases():
        parsed = parse_request(case)
        assert parsed.operation == case["operation"]
        assert parsed.inputs == case["inputs"]


def test_direct_planning_baseline_reports_required_metrics() -> None:
    report = run_planning_baseline(planning_cases())
    metrics = report["planning_metrics"]
    assert metrics["task_pass_rate"] == 1.0
    assert metrics["successful_plans"] == 18
    assert metrics["constraint_violation_rate"] == 0.0
    assert metrics["mean_optimality_gap"] == 0.0
    assert metrics["retry_cases"] == 3
    assert metrics["retry_recovery_rate"] == 1.0
    assert metrics["expected_clarifications"] == 6
    assert metrics["clarification_accuracy"] == 1.0
    assert metrics["premature_stops"] == 0
    assert metrics["duplicate_successful_steps"] == 0


def test_rule_planning_baseline_matches_controlled_templates() -> None:
    report = run_rule_planning_baseline(planning_cases())
    assert report["summary"]["parse_exact_rate"] == 1.0
    assert report["planning_metrics"]["task_pass_rate"] == 1.0
    assert report["planning_metrics"]["constraint_violation_rate"] == 0.0
