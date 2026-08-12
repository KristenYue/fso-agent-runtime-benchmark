import hashlib
import json
from pathlib import Path

import pytest

from fso_benchmark.development_gate import assess_development_artifacts


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def build_valid_artifacts(root: Path) -> None:
    dataset_path = root / "data" / "tasks_v2.json"
    contract_path = root / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    write_json(
        dataset_path,
        {
            "tasks": [
                {"task_id": "plan-1", "operation": "plan_turbulence_aware_link"},
                {"task_id": "other-1", "operation": "characterize_turbulence"},
            ]
        },
    )
    write_json(contract_path, {"contract": "test"})
    output = root / "artifacts" / "langgraph_model_development"
    write_json(
        output / "manifest.json",
        {
            "development_dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            "challenge_tasks_run": 0,
            "credentials_recorded": False,
        },
    )
    write_json(
        output / "results.json",
        {
            "summary": {"total": 1, "passed": 1, "pass_rate": 1.0, "model_calls": 2},
            "model_telemetry": [{"call_index": 1}, {"call_index": 2}],
            "results": [{"task_id": "plan-1", "passed": True}],
        },
    )


def test_accepts_complete_development_artifacts(tmp_path: Path) -> None:
    build_valid_artifacts(tmp_path)
    report = assess_development_artifacts(tmp_path)
    assert report == {
        "status": "valid",
        "planning_tasks": 1,
        "passed": 1,
        "pass_rate": 1.0,
        "model_calls": 2,
        "challenge_tasks_run": 0,
        "ready_for_final_configuration_review": True,
    }


def test_rejects_incomplete_task_coverage(tmp_path: Path) -> None:
    build_valid_artifacts(tmp_path)
    results_path = tmp_path / "artifacts" / "langgraph_model_development" / "results.json"
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["results"] = []
    write_json(results_path, payload)
    with pytest.raises(ValueError, match="exactly cover"):
        assess_development_artifacts(tmp_path)


def test_rejects_credential_like_fields(tmp_path: Path) -> None:
    build_valid_artifacts(tmp_path)
    results_path = tmp_path / "artifacts" / "langgraph_model_development" / "results.json"
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["api_key"] = "must-not-be-recorded"
    write_json(results_path, payload)
    with pytest.raises(ValueError, match="credential-like"):
        assess_development_artifacts(tmp_path)
