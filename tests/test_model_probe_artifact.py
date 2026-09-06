import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("iteration", ["iteration_01", "iteration_02"])
def test_archived_successful_probe_is_bound_to_its_contract_and_contains_no_credentials(
    iteration: str,
) -> None:
    iteration_path = ROOT / "artifacts" / "langgraph_model_development_runs" / iteration
    probe_path = iteration_path / "probe.json"
    contract_path = iteration_path / "model_contract.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert probe["passed"] is True
    assert probe["challenge_tasks_run"] == 0
    assert probe["credentials_recorded"] is False
    assert probe["contract_sha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert probe["provider"] == contract["model"]["provider"]
    assert probe["base_url"] == contract["model"]["base_url"]
    assert probe["snapshot_id"] == contract["model"]["snapshot_id"]
    assert probe["action"]["kind"] == probe["expected"]["kind"] == "finish"
    assert probe["action"]["status"] == probe["expected"]["status"] == "needs_clarification"
    assert probe["error"] is None

    serialized = json.dumps(probe).lower()
    for forbidden in ("api_key", "authorization", "bearer ", "access_token", "secret_key"):
        assert forbidden not in serialized


@pytest.mark.parametrize("iteration", ["iteration_01", "iteration_02"])
def test_successful_probe_has_one_complete_provider_telemetry_record(iteration: str) -> None:
    probe_path = (
        ROOT
        / "artifacts"
        / "langgraph_model_development_runs"
        / iteration
        / "probe.json"
    )
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    telemetry = probe["model_telemetry"]

    assert len(telemetry) == 1
    call = telemetry[0]
    assert call["call_index"] == 1
    assert call["step"] == 0
    assert call["attempts"] == 1
    assert call["status_code"] == 200
    assert call["elapsed_ms"] > 0
    assert call["prompt_tokens"] > 0
    assert call["completion_tokens"] > 0
    assert call["total_tokens"] == call["prompt_tokens"] + call["completion_tokens"]
    assert call["provider_request_id"]
    assert call["idempotency_key"].startswith("fso-")


def test_iteration_02_development_artifacts_are_complete_and_secret_free() -> None:
    iteration_path = (
        ROOT / "artifacts" / "langgraph_model_development_runs" / "iteration_02"
    )
    manifest = json.loads((iteration_path / "manifest.json").read_text(encoding="utf-8"))
    results = json.loads((iteration_path / "results.json").read_text(encoding="utf-8"))

    assert manifest["challenge_tasks_run"] == 0
    assert manifest["credentials_recorded"] is False
    assert results["summary"]["total"] == results["summary"]["passed"] == 30
    assert results["planning_metrics"]["constraint_violations"] == 0
    assert results["planning_metrics"]["persistent_fault_cases"] == 3
    assert results["planning_metrics"]["correct_persistent_stops"] == 3
    assert results["failure_analysis"] == {
        "failed_tasks": 0,
        "category_counts": {"passed": 30},
    }

    serialized = json.dumps({"manifest": manifest, "results": results}).lower()
    for forbidden in ("api_key", "authorization", "bearer ", "access_token", "secret_key"):
        assert forbidden not in serialized
