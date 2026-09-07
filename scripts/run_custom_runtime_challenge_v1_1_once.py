from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.agent_runtime import run_agent  # noqa: E402
from fso_benchmark.baseline import matches_expected  # noqa: E402
from fso_benchmark.contracts import TaskResult  # noqa: E402
from fso_benchmark.custom_runtime_contract import CONTRACT_PATH, sha256  # noqa: E402
from fso_benchmark.development_gate import assess_development_artifacts  # noqa: E402
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402
from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402
from fso_benchmark.recovery_contract import (  # noqa: E402
    RECOVERY_CONTRACT_PATH,
    load_and_validate_recovery_contract,
    validate_api_key,
)


APPROVAL_VALUE = "custom-runtime-challenge-recovery-v1-1-final-once"


def require_successful_probe(root: Path, contract: dict) -> dict:
    path = root / contract["new_artifacts"]["probe_path"]
    if not path.exists():
        raise ValueError("successful recovery credential probe is missing")
    probe = json.loads(path.read_text(encoding="utf-8"))
    model = contract["model"]
    if probe.get("passed") is not True or probe.get("error") is not None:
        raise ValueError("recovery credential probe did not pass")
    if probe.get("recovery_contract_sha256") != sha256(root / RECOVERY_CONTRACT_PATH):
        raise ValueError("recovery credential probe contract hash mismatch")
    if probe.get("challenge_tasks_loaded") != 0 or probe.get("challenge_tasks_run") != 0:
        raise ValueError("recovery probe touched Challenge tasks")
    for probe_key, model_key in (
        ("provider", "provider"),
        ("base_url", "base_url"),
        ("snapshot_id", "snapshot_id"),
    ):
        if probe.get(probe_key) != model[model_key]:
            raise ValueError(f"recovery credential probe {probe_key} mismatch")
    telemetry = probe.get("model_telemetry")
    if (
        not isinstance(telemetry, list)
        or len(telemetry) != 1
        or telemetry[0].get("attempts") != 1
        or telemetry[0].get("status_code") != 200
    ):
        raise ValueError("recovery credential probe did not record one HTTP 200 attempt")
    return probe


def require_final_configuration() -> tuple[str, str, str, str, dict, dict, dict]:
    provider = os.environ.get("FSO_MODEL_PROVIDER", "")
    base_url = os.environ.get("FSO_MODEL_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("FSO_MODEL_API_KEY", "")
    model = os.environ.get("FSO_MODEL_ID", "")
    try:
        validate_api_key(api_key)
    except ValueError as exc:
        raise SystemExit(f"credential preflight failed: {exc}") from exc
    if os.environ.get("FSO_CUSTOM_RUNTIME_RECOVERY_APPROVAL") != APPROVAL_VALUE:
        raise SystemExit("custom Runtime recovery approval is missing")
    try:
        contract = load_and_validate_recovery_contract(ROOT)
        expected = contract["model"]
        actual = {
            "provider": provider,
            "base_url": base_url,
            "snapshot_id": model,
        }
        for key, value in actual.items():
            if value != expected[key]:
                raise ValueError(f"recovery model {key} mismatch")
        probe = require_successful_probe(ROOT, contract)
        development_dir = ROOT / "artifacts" / "custom_runtime_development"
        assessment = assess_development_artifacts(
            ROOT,
            output_dir=development_dir,
            contract_path=ROOT / CONTRACT_PATH,
        )
        if assessment["planning_tasks"] != 30:
            raise ValueError("development does not contain all 30 planning tasks")
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"recovery preflight failed: {exc}") from exc
    development = json.loads(
        (ROOT / contract["frozen_inputs"]["development_manifest_path"]).read_text(
            encoding="utf-8"
        )
    )
    output_dir = ROOT / contract["new_artifacts"]["challenge_directory"]
    if (output_dir / "run_ledger.json").exists():
        raise SystemExit("recovery Challenge has already been reserved or executed")
    return provider, base_url, api_key, model, contract, development, probe


def main() -> None:
    provider, base_url, api_key, model, contract, development, probe = (
        require_final_configuration()
    )
    output_dir = ROOT / contract["new_artifacts"]["challenge_directory"]
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "run_ledger.json"
    ledger = {
        "schema_version": "1.1",
        "challenge": "challenge-v1-custom-runtime-incident-recovery-v1-1",
        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "model_id": model,
        "model_provider": provider,
        "base_url": base_url,
        "recovery_contract_sha256": sha256(ROOT / RECOVERY_CONTRACT_PATH),
        "original_incident_preserved": True,
        "credentials_recorded": False,
    }
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    policy = contract["runtime_policy"]
    model_policy = contract["model"]
    challenge_path = ROOT / contract["frozen_inputs"]["challenge_path"]
    cases = json.loads(challenge_path.read_text(encoding="utf-8"))["tasks"]
    planner = OpenAICompatiblePlanner(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt_path=ROOT / "prompts" / "planner_v1.md",
        schema_path=ROOT / "schemas" / "planner_action_v1.json",
        temperature=model_policy["temperature"],
        timeout_seconds=policy["request_timeout_seconds"],
        retry_budget=policy["provider_retry_budget"],
        response_format_type=model_policy["response_format_type"],
        enable_thinking=model_policy["enable_thinking"],
        idempotency_namespace=policy["idempotency_namespace"],
    )
    records = []
    for case in cases:
        started = time.perf_counter()
        result = run_agent(
            case["request"],
            planner,
            max_tool_calls=policy["max_tool_calls"],
            fault_profile=case["inputs"].get("injected_fault"),
        )
        task_result = TaskResult(
            task_id=case["task_id"],
            status=result["status"],
            answer=result["answer"],
            error=result["error"],
            trace=tuple(result["trace"]),
        )
        records.append(
            {
                "task_id": case["task_id"],
                **result,
                "passed": matches_expected(task_result, case["expected"]),
                "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            }
        )
    usage = planner.usage_summary()
    scored = score_planning_report(cases, {"results": records})
    total = len(records)
    report = {
        "summary": {
            "total": total,
            "passed": sum(row["passed"] for row in records),
            "pass_rate": sum(row["passed"] for row in records) / total,
            **usage,
        },
        "planning_metrics": scored["planning_metrics"],
        "failure_analysis": scored["failure_analysis"],
        "model_telemetry": planner.telemetry_records(),
        "results": records,
    }
    results_path = output_dir / "results.json"
    results_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ledger.update(
        {
            "status": "complete",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "probe_sha256": hashlib.sha256(
                json.dumps(probe, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "development_manifest_sha256": hashlib.sha256(
                json.dumps(development, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "result_sha256": sha256(results_path),
        }
    )
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
