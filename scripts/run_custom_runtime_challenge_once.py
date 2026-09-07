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
from fso_benchmark.custom_runtime_contract import (  # noqa: E402
    CONTRACT_PATH,
    load_and_validate_contract,
    runtime_source_hashes,
    sha256,
    validate_model_environment,
)
from fso_benchmark.development_gate import assess_development_artifacts  # noqa: E402
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402
from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402


APPROVAL_VALUE = "custom-runtime-challenge-v1-final-once"


def require_final_configuration() -> tuple[str, str, str, str, dict, dict]:
    provider = os.environ.get("FSO_MODEL_PROVIDER", "")
    base_url = os.environ.get("FSO_MODEL_BASE_URL", "")
    api_key = os.environ.get("FSO_MODEL_API_KEY", "")
    model = os.environ.get("FSO_MODEL_ID", "")
    if not all((provider, base_url, api_key, model)):
        raise SystemExit("model configuration is incomplete")
    if os.environ.get("FSO_CUSTOM_RUNTIME_CHALLENGE_APPROVAL") != APPROVAL_VALUE:
        raise SystemExit("frozen custom Runtime challenge approval is missing")
    try:
        contract = load_and_validate_contract(ROOT)
        validate_model_environment(
            contract, provider=provider, base_url=base_url, model=model
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"custom Runtime contract validation failed: {exc}") from exc

    development_dir = ROOT / "artifacts" / "custom_runtime_development"
    manifest_path = development_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("custom Runtime development manifest is required")
    development = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_identity = contract["model"]
    if (
        development.get("model_provider") != expected_identity["provider"]
        or development.get("model_id") != expected_identity["snapshot_id"]
        or development.get("base_url") != expected_identity["base_url"]
    ):
        raise SystemExit("model configuration differs from custom Runtime development")
    contract_path = ROOT / CONTRACT_PATH
    if development.get("contract_sha256") != sha256(contract_path):
        raise SystemExit("custom Runtime contract differs from development manifest")
    if development.get("runtime_source_sha256") != runtime_source_hashes(ROOT):
        raise SystemExit("custom Runtime source differs from development manifest")
    try:
        assessment = assess_development_artifacts(
            ROOT, output_dir=development_dir, contract_path=contract_path
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"development artifact validation failed: {exc}") from exc
    if assessment["planning_tasks"] != 30:
        raise SystemExit("development artifact must contain all 30 planning tasks")

    output_dir = ROOT / "artifacts" / "custom_runtime_challenge"
    if (output_dir / "run_ledger.json").exists():
        raise SystemExit("custom Runtime challenge has already been reserved or executed")
    return provider, base_url.rstrip("/"), api_key, model, contract, development


def main() -> None:
    provider, base_url, api_key, model, contract, development = require_final_configuration()
    output_dir = ROOT / "artifacts" / "custom_runtime_challenge"
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "run_ledger.json"
    ledger = {
        "schema_version": "1.0",
        "challenge": "challenge-v1-custom-runtime",
        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "model_id": model,
        "model_provider": provider,
        "base_url": base_url,
        "credentials_recorded": False,
    }
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    policy = contract["runtime_policy"]
    model_policy = contract["model"]
    challenge_path = ROOT / contract["datasets"]["challenge_path"]
    cases = json.loads(challenge_path.read_text(encoding="utf-8"))["tasks"]
    planner = OpenAICompatiblePlanner(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt_path=ROOT / contract["frozen_components"]["prompt_path"],
        schema_path=ROOT / contract["frozen_components"]["action_schema_path"],
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
            "contract_sha256": sha256(ROOT / CONTRACT_PATH),
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
