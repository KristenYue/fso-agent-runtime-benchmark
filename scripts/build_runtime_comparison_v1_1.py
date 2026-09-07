from __future__ import annotations

import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.planning_metrics import score_planning_report  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def configuration_id(row: dict) -> str | None:
    answer = row.get("answer") or {}
    return (answer.get("selection") or {}).get("configuration_id")


def main() -> None:
    challenge_path = ROOT / "data" / "challenge_v1.json"
    langgraph_path = ROOT / "artifacts" / "langgraph_model_challenge" / "results.json"
    custom_path = ROOT / "artifacts" / "custom_runtime_challenge_v1_1" / "results.json"
    custom_ledger_path = custom_path.parent / "run_ledger.json"
    incident_path = ROOT / "artifacts" / "custom_runtime_challenge" / "results.json"
    offline_path = ROOT / "artifacts" / "runtime_overhead_v1" / "results.json"

    cases = json.loads(challenge_path.read_text(encoding="utf-8"))["tasks"]
    langgraph = json.loads(langgraph_path.read_text(encoding="utf-8"))
    custom = json.loads(custom_path.read_text(encoding="utf-8"))
    custom_ledger = json.loads(custom_ledger_path.read_text(encoding="utf-8"))
    incident = json.loads(incident_path.read_text(encoding="utf-8"))
    offline = json.loads(offline_path.read_text(encoding="utf-8"))
    if sha256(custom_path) != custom_ledger["result_sha256"]:
        raise ValueError("custom recovery result hash differs from ledger")
    if incident["summary"]["calls"] != 0 or incident["summary"]["attempts"] != 0:
        raise ValueError("original incident disclosure is not a zero-call artifact")

    langgraph_scored = score_planning_report(cases, langgraph)
    custom_scored = score_planning_report(cases, custom)
    langgraph_rows = {row["task_id"]: row for row in langgraph["results"]}
    custom_rows = {row["task_id"]: row for row in custom["results"]}
    expected_ids = {case["task_id"] for case in cases}
    if set(langgraph_rows) != expected_ids or set(custom_rows) != expected_ids:
        raise ValueError("comparison results do not cover the same Challenge task IDs")

    pairs = []
    for task_id in sorted(expected_ids):
        baseline = langgraph_rows[task_id]
        candidate = custom_rows[task_id]
        pairs.append(
            {
                "task_id": task_id,
                "langgraph_passed": baseline["passed"],
                "custom_passed": candidate["passed"],
                "status_match": baseline["status"] == candidate["status"],
                "configuration_match": configuration_id(baseline)
                == configuration_id(candidate),
                "trace_exact_match": baseline["trace"] == candidate["trace"],
                "answer_exact_match": baseline["answer"] == candidate["answer"],
                "langgraph_tool_calls": len(baseline["trace"]),
                "custom_tool_calls": len(candidate["trace"]),
            }
        )

    langgraph_latencies = [row["elapsed_ms"] for row in langgraph["results"]]
    custom_latencies = [row["elapsed_ms"] for row in custom["results"]]
    report = {
        "schema_version": "1.0",
        "comparison": "langgraph_vs_custom_runtime_incident_recovery_v1_1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disclosure": {
            "original_custom_v1_was_infrastructure_incident": True,
            "original_v1_model_calls": 0,
            "original_v1_raw_passed": 0,
            "recovery_uses_same_24_tasks": True,
            "evidence_strength": "lower_than_an_uninterrupted_preregistered_single_run",
        },
        "frozen_challenge": {
            "tasks": len(cases),
            "sha256": sha256(challenge_path),
        },
        "langgraph": {
            "result_sha256": sha256(langgraph_path),
            "summary": langgraph["summary"],
            "rescored_planning_metrics": langgraph_scored["planning_metrics"],
            "rescored_failure_analysis": langgraph_scored["failure_analysis"],
            "p50_task_latency_ms": statistics.median(langgraph_latencies),
            "p95_task_latency_ms": percentile(langgraph_latencies, 0.95),
        },
        "custom_runtime_recovery_v1_1": {
            "result_sha256": sha256(custom_path),
            "ledger_sha256": sha256(custom_ledger_path),
            "summary": custom["summary"],
            "rescored_planning_metrics": custom_scored["planning_metrics"],
            "rescored_failure_analysis": custom_scored["failure_analysis"],
            "p50_task_latency_ms": statistics.median(custom_latencies),
            "p95_task_latency_ms": percentile(custom_latencies, 0.95),
        },
        "paired": {
            "strict_pass_difference_custom_minus_langgraph": custom["summary"]["passed"]
            - langgraph["summary"]["passed"],
            "status_matches": sum(row["status_match"] for row in pairs),
            "configuration_matches": sum(row["configuration_match"] for row in pairs),
            "trace_exact_matches": sum(row["trace_exact_match"] for row in pairs),
            "answer_exact_matches": sum(row["answer_exact_match"] for row in pairs),
            "model_call_difference": custom["summary"]["calls"]
            - langgraph["summary"]["calls"],
            "prompt_token_difference": custom["summary"]["prompt_tokens"]
            - langgraph["summary"]["prompt_tokens"],
            "completion_token_difference": custom["summary"]["completion_tokens"]
            - langgraph["summary"]["completion_tokens"],
            "total_elapsed_difference_ms": custom["summary"]["elapsed_ms"]
            - langgraph["summary"]["elapsed_ms"],
            "tasks": pairs,
        },
        "offline_scheduler_evidence": {
            "artifact_sha256": sha256(offline_path),
            "pairs": offline["method"]["pairs"],
            "langgraph_median_us": offline["langgraph"]["median_us"],
            "custom_runtime_median_us": offline["custom_runtime"]["median_us"],
            "median_speedup_ratio": offline["median_speedup_ratio"],
            "paired_median_difference_us": offline["paired_difference"]["median_us"],
            "interpretation": "Local scheduler evidence only; model-network latency dominates end-to-end runs.",
        },
    }
    output = ROOT / "artifacts" / "runtime_comparison_v1_1" / "report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["paired"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
