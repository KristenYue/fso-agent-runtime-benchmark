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
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def require_environment() -> tuple[str, str, str]:
    values = (
        os.environ.get("FSO_MODEL_BASE_URL", ""),
        os.environ.get("FSO_MODEL_API_KEY", ""),
        os.environ.get("FSO_MODEL_ID", ""),
    )
    missing = [
        name
        for name, value in zip(
            ("FSO_MODEL_BASE_URL", "FSO_MODEL_API_KEY", "FSO_MODEL_ID"), values
        )
        if not value
    ]
    if missing:
        raise SystemExit("missing required model configuration: " + ", ".join(missing))
    return values


def main() -> None:
    base_url, api_key, model = require_environment()
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
    )
    records = []
    latencies = []
    for case in cases:
        started = time.perf_counter()
        result = run_agent(case["request"], planner, max_tool_calls=8)
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
        "cost": None,
        "cost_note": "Provider price and price date must be supplied before cost is reported.",
    }
    output_dir = ROOT / "artifacts" / "langgraph_model_development"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps({"summary": summary, "results": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    contract_path = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    manifest = {
        "schema_version": "1.0",
        "experiment": "langgraph_model_development",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "model_id": model,
        "base_url": base_url,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "challenge_tasks_run": 0,
        "credentials_recorded": False,
        "configuration_selection_only": True,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
