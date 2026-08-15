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

from fso_benchmark.baseline import matches_expected  # noqa: E402
from fso_benchmark.contracts import TaskResult  # noqa: E402
from fso_benchmark.langgraph_agent import run_agent  # noqa: E402
from fso_benchmark.model_planner import (  # noqa: E402
    OpenAICompatiblePlanner,
    calculate_token_cost,
)
from fso_benchmark.model_contract import require_bound_model_contract  # noqa: E402
from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def require_environment() -> tuple[str, str, str, str]:
    values = (
        os.environ.get("FSO_MODEL_PROVIDER", ""),
        os.environ.get("FSO_MODEL_BASE_URL", ""),
        os.environ.get("FSO_MODEL_API_KEY", ""),
        os.environ.get("FSO_MODEL_ID", ""),
    )
    missing = [
        name
        for name, value in zip(
            (
                "FSO_MODEL_PROVIDER",
                "FSO_MODEL_BASE_URL",
                "FSO_MODEL_API_KEY",
                "FSO_MODEL_ID",
            ),
            values,
        )
        if not value
    ]
    if missing:
        raise SystemExit("missing required model configuration: " + ", ".join(missing))
    return values


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


def main() -> None:
    provider, base_url, api_key, model = require_environment()
    try:
        contract = require_bound_model_contract(
            ROOT, provider=provider, base_url=base_url, snapshot_id=model
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"model contract validation failed: {exc}") from exc
    provider = contract["model"]["provider"]
    base_url = contract["model"]["base_url"]
    model = contract["model"]["snapshot_id"]
    pricing = price_configuration()
    dataset_path = ROOT / "data" / "tasks_v2.json"
    dataset_bytes = dataset_path.read_bytes()
    payload = json.loads(dataset_bytes)
    cases = [
        case
        for case in payload["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]
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
    latencies = []
    for case in cases:
        started = time.perf_counter()
        result = run_agent(
            case["request"],
            planner,
            max_tool_calls=8,
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
    total = len(records)
    cost = None
    if pricing is not None and usage["usage_complete"]:
        cost = calculate_token_cost(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            input_price_per_million=pricing["input_price_per_million"],
            output_price_per_million=pricing["output_price_per_million"],
        )
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
    output_dir = ROOT / "artifacts" / "langgraph_model_development"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "planning_metrics": scored["planning_metrics"],
                "failure_analysis": scored["failure_analysis"],
                "model_telemetry": planner.telemetry_records(),
                "results": records,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    contract_path = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    manifest = {
        "schema_version": "1.0",
        "experiment": "langgraph_model_development",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "model_id": model,
        "model_provider": provider,
        "base_url": base_url,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
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
