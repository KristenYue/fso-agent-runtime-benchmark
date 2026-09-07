from __future__ import annotations

import hashlib
import json
import os
import statistics
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
    validate_model_environment,
)
from fso_benchmark.model_planner import (  # noqa: E402
    OpenAICompatiblePlanner,
    calculate_token_cost,
)
from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402


def require_environment() -> tuple[str, str, str, str]:
    names = (
        "FSO_MODEL_PROVIDER",
        "FSO_MODEL_BASE_URL",
        "FSO_MODEL_API_KEY",
        "FSO_MODEL_ID",
    )
    values = tuple(os.environ.get(name, "") for name in names)
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise SystemExit("missing required model configuration: " + ", ".join(missing))
    return values  # type: ignore[return-value]


def price_configuration() -> dict | None:
    names = (
        "FSO_MODEL_INPUT_PRICE_PER_MILLION",
        "FSO_MODEL_OUTPUT_PRICE_PER_MILLION",
        "FSO_MODEL_PRICE_DATE",
        "FSO_MODEL_PRICE_CURRENCY",
    )
    values = {name: os.environ.get(name, "") for name in names}
    if not any(values.values()):
        return None
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SystemExit("incomplete price configuration: " + ", ".join(missing))
    try:
        input_price = float(values[names[0]])
        output_price = float(values[names[1]])
    except ValueError as exc:
        raise SystemExit("model prices must be numeric") from exc
    if input_price < 0 or output_price < 0:
        raise SystemExit("model prices must be non-negative")
    return {
        "input_price_per_million": input_price,
        "output_price_per_million": output_price,
        "price_date": values[names[2]],
        "currency": values[names[3]],
    }


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def main() -> None:
    provider, base_url, api_key, model = require_environment()
    try:
        contract = load_and_validate_contract(ROOT)
        validate_model_environment(
            contract, provider=provider, base_url=base_url, model=model
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"custom Runtime contract validation failed: {exc}") from exc

    dataset_path = ROOT / contract["datasets"]["development_path"]
    dataset_bytes = dataset_path.read_bytes()
    cases = [
        case
        for case in json.loads(dataset_bytes)["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]
    policy = contract["runtime_policy"]
    model_policy = contract["model"]
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
    latencies = []
    for case in cases:
        started = time.perf_counter()
        result = run_agent(
            case["request"],
            planner,
            max_tool_calls=policy["max_tool_calls"],
            fault_profile=case["inputs"].get("injected_fault"),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(elapsed_ms)
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
                "elapsed_ms": elapsed_ms,
            }
        )

    usage = planner.usage_summary()
    scored = score_planning_report(cases, {"results": records})
    pricing = price_configuration()
    cost = None
    if pricing is not None and usage["usage_complete"]:
        cost = calculate_token_cost(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            input_price_per_million=pricing["input_price_per_million"],
            output_price_per_million=pricing["output_price_per_million"],
        )
    total = len(records)
    summary = {
        "total": total,
        "passed": sum(row["passed"] for row in records),
        "pass_rate": sum(row["passed"] for row in records) / total,
        "p50_task_latency_ms": statistics.median(latencies),
        "p95_task_latency_ms": percentile(latencies, 0.95),
        "model_calls": usage["calls"],
        "provider_attempts": usage["attempts"],
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "usage_complete": usage["usage_complete"],
        "cost": cost,
        "cost_note": (
            "Computed from supplied price metadata."
            if cost is not None
            else "Cost omitted until complete provider usage and dated price metadata are supplied."
        ),
    }
    output_dir = ROOT / "artifacts" / "custom_runtime_development"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "summary": summary,
        "planning_metrics": scored["planning_metrics"],
        "failure_analysis": scored["failure_analysis"],
        "model_telemetry": planner.telemetry_records(),
        "results": records,
    }
    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    contract_path = ROOT / CONTRACT_PATH
    manifest = {
        "schema_version": "1.0",
        "experiment": "custom_runtime_development",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "model_id": model,
        "model_provider": provider,
        "base_url": base_url.rstrip("/"),
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "runtime_source_sha256": runtime_source_hashes(ROOT),
        "challenge_tasks_run": 0,
        "credentials_recorded": False,
        "configuration_selection_only": True,
        "pricing": pricing,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
