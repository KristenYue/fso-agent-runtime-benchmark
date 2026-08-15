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

from fso_benchmark.baseline import matches_expected  # noqa: E402
from fso_benchmark.contracts import TaskResult  # noqa: E402
from fso_benchmark.development_gate import assess_development_artifacts  # noqa: E402
from fso_benchmark.langgraph_agent import run_agent  # noqa: E402
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402
from fso_benchmark.model_contract import require_bound_model_contract  # noqa: E402
from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402


FROZEN_CHALLENGE_SHA256 = "4d905a08b1b52a3be271daa53f1a9596fca16cfc5091fcfa9d2fe1a30b5f9086"
APPROVAL_VALUE = "challenge-v1-final-once"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_final_configuration() -> tuple[str, str, str, str, dict]:
    provider = os.environ.get("FSO_MODEL_PROVIDER", "")
    base_url = os.environ.get("FSO_MODEL_BASE_URL", "")
    api_key = os.environ.get("FSO_MODEL_API_KEY", "")
    model = os.environ.get("FSO_MODEL_ID", "")
    if not all((provider, base_url, api_key, model)):
        raise SystemExit("model configuration is incomplete")
    if os.environ.get("FSO_FROZEN_CHALLENGE_APPROVAL") != APPROVAL_VALUE:
        raise SystemExit("frozen challenge approval is missing")
    try:
        contract = require_bound_model_contract(
            ROOT, provider=provider, base_url=base_url, snapshot_id=model
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"model contract validation failed: {exc}") from exc
    provider = contract["model"]["provider"]
    base_url = contract["model"]["base_url"]
    model = contract["model"]["snapshot_id"]
    development_manifest_path = (
        ROOT / "artifacts" / "langgraph_model_development" / "manifest.json"
    )
    if not development_manifest_path.exists():
        raise SystemExit("development model manifest is required before frozen challenge")
    development = json.loads(development_manifest_path.read_text(encoding="utf-8"))
    if (
        development.get("model_provider") != provider
        or development.get("model_id") != model
        or development.get("base_url") != base_url
    ):
        raise SystemExit("model configuration differs from development manifest")
    contract_path = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    if not contract_path.exists():
        raise SystemExit("frozen model contract is missing")
    if development.get("contract_sha256") != sha256(contract_path):
        raise SystemExit("frozen model contract differs from development manifest")
    try:
        assess_development_artifacts(ROOT)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"development artifact validation failed: {exc}") from exc
    ledger_path = ROOT / "artifacts" / "langgraph_model_challenge" / "run_ledger.json"
    if ledger_path.exists():
        raise SystemExit("frozen challenge has already been reserved or executed")
    challenge_path = ROOT / "data" / "challenge_v1.json"
    if sha256(challenge_path) != FROZEN_CHALLENGE_SHA256:
        raise SystemExit("frozen challenge hash mismatch")
    return provider, base_url, api_key, model, development


def main() -> None:
    provider, base_url, api_key, model, development = require_final_configuration()
    output_dir = ROOT / "artifacts" / "langgraph_model_challenge"
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "run_ledger.json"
    ledger = {
        "schema_version": "1.0",
        "challenge": "challenge-v1",
        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "model_id": model,
        "model_provider": provider,
        "base_url": base_url,
        "credentials_recorded": False,
    }
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    challenge_path = ROOT / "data" / "challenge_v1.json"
    cases = json.loads(challenge_path.read_text(encoding="utf-8"))["tasks"]
    planner = OpenAICompatiblePlanner(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt_path=ROOT / "prompts" / "planner_v1.md",
        schema_path=ROOT / "schemas" / "planner_action_v1.json",
        temperature=0.0,
        timeout_seconds=30.0,
        retry_budget=1,
        response_format_type=contract["model"]["response_format_type"],
        enable_thinking=contract["model"]["enable_thinking"],
    )
    records = []
    for case in cases:
        started = time.perf_counter()
        result = run_agent(
            case["request"],
            planner,
            max_tool_calls=8,
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
    total = len(records)
    usage = planner.usage_summary()
    scored = score_planning_report(cases, {"results": records})
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
    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ledger.update(
        {
            "status": "complete",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "development_manifest_sha256": hashlib.sha256(
                json.dumps(development, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "result_sha256": sha256(output_dir / "results.json"),
        }
    )
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
