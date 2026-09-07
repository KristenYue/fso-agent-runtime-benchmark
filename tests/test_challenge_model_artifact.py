import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "langgraph_model_challenge"


def test_frozen_model_challenge_is_complete_and_hash_bound() -> None:
    ledger = json.loads((ARTIFACT_DIR / "run_ledger.json").read_text(encoding="utf-8"))
    result_path = ARTIFACT_DIR / "results.json"
    results = json.loads(result_path.read_text(encoding="utf-8"))

    assert ledger["status"] == "complete"
    assert ledger["credentials_recorded"] is False
    assert ledger["result_sha256"] == hashlib.sha256(result_path.read_bytes()).hexdigest()
    assert results["summary"]["total"] == results["summary"]["passed"] == 24
    assert results["planning_metrics"]["constraint_violations"] == 0
    assert results["failure_analysis"] == {
        "failed_tasks": 0,
        "category_counts": {"passed": 24},
    }


def test_posthoc_correction_preserves_raw_result_and_records_no_rerun() -> None:
    result_path = ARTIFACT_DIR / "results.json"
    correction = json.loads(
        (ARTIFACT_DIR / "posthoc_metrics_correction_2026-09-07.json").read_text(
            encoding="utf-8"
        )
    )

    assert correction["source_result_sha256"] == hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()
    assert correction["challenge_rerun"] is False
    assert correction["model_calls_added"] == 0
    assert correction["changed_metrics"] == {
        "duplicate_successful_steps": {"original": 4, "corrected": 0}
    }
    assert correction["planning_metrics"]["duplicate_successful_steps"] == 0


def test_frozen_model_challenge_artifacts_contain_no_credentials() -> None:
    serialized = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in ARTIFACT_DIR.glob("*.json")
    )
    for forbidden in (
        "api_key",
        "authorization",
        "bearer ",
        "access_token",
        "secret_key",
        "sk-ws-",
        "sk-sp-",
    ):
        assert forbidden not in serialized
