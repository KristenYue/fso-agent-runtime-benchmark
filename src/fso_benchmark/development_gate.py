"""Integrity checks for the LangGraph model development artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_CREDENTIAL_KEYS = {"api_key", "authorization", "access_token", "secret"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"required artifact is missing: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"artifact must contain a JSON object: {path.name}")
    return value


def _contains_credential_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in FORBIDDEN_CREDENTIAL_KEYS
            or _contains_credential_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_credential_key(child) for child in value)
    return False


def assess_development_artifacts(
    root: Path, *, output_dir: Path | None = None
) -> dict[str, Any]:
    dataset_path = root / "data" / "tasks_v2.json"
    contract_path = root / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    if output_dir is None:
        output_dir = root / "artifacts" / "langgraph_model_development"
    manifest = _load_object(output_dir / "manifest.json")
    payload = _load_object(output_dir / "results.json")
    dataset = _load_object(dataset_path)

    if manifest.get("development_dataset_sha256") != _sha256(dataset_path):
        raise ValueError("development dataset hash mismatch")
    if not contract_path.exists() or manifest.get("contract_sha256") != _sha256(contract_path):
        raise ValueError("frozen model contract hash mismatch")
    if manifest.get("challenge_tasks_run") != 0:
        raise ValueError("development manifest must record zero challenge runs")
    if manifest.get("credentials_recorded") is not False:
        raise ValueError("development manifest must record that credentials are excluded")

    expected_ids = [
        case["task_id"]
        for case in dataset.get("tasks", [])
        if case.get("operation") == "plan_turbulence_aware_link"
    ]
    records = payload.get("results")
    telemetry = payload.get("model_telemetry")
    summary = payload.get("summary")
    planning_metrics = payload.get("planning_metrics")
    failure_analysis = payload.get("failure_analysis")
    if not expected_ids or not isinstance(records, list) or not isinstance(summary, dict):
        raise ValueError("development artifact structure is invalid")
    actual_ids = [row.get("task_id") for row in records if isinstance(row, dict)]
    if len(actual_ids) != len(records) or len(set(actual_ids)) != len(actual_ids):
        raise ValueError("development results contain invalid or duplicate task IDs")
    if set(actual_ids) != set(expected_ids):
        raise ValueError("development results do not exactly cover planning tasks")
    passed = sum(row.get("passed") is True for row in records)
    if summary.get("total") != len(records) or summary.get("passed") != passed:
        raise ValueError("development summary counts do not match task records")
    expected_rate = passed / len(records)
    if summary.get("pass_rate") != expected_rate:
        raise ValueError("development summary pass rate does not match task records")
    if not isinstance(telemetry, list) or not telemetry:
        raise ValueError("development model telemetry is missing")
    if summary.get("model_calls") != len(telemetry):
        raise ValueError("development model-call count does not match telemetry")
    if not isinstance(planning_metrics, dict) or planning_metrics.get("total") != len(records):
        raise ValueError("development planning metrics are missing or incomplete")
    if not isinstance(failure_analysis, dict):
        raise ValueError("development failure analysis is missing")
    categories = failure_analysis.get("category_counts")
    if not isinstance(categories, dict) or sum(categories.values()) != len(records):
        raise ValueError("development failure categories do not cover all tasks")
    if failure_analysis.get("failed_tasks") != len(records) - passed:
        raise ValueError("development failure count does not match task records")
    if _contains_credential_key({"manifest": manifest, "payload": payload}):
        raise ValueError("development artifacts contain a credential-like field")

    return {
        "status": "valid",
        "planning_tasks": len(records),
        "passed": passed,
        "pass_rate": expected_rate,
        "model_calls": len(telemetry),
        "failed_tasks": len(records) - passed,
        "challenge_tasks_run": 0,
        "ready_for_final_configuration_review": True,
    }
