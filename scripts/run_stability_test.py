"""Run an offline, deterministic Runtime soak test without model or network calls."""

from __future__ import annotations

import argparse
from collections import deque
import gc
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.agent_runtime import run_agent  # noqa: E402
from fso_benchmark.planner_contract import ScriptedPlanner  # noqa: E402


def happy_actions() -> list[dict[str, Any]]:
    return [
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 0.75}},
        {"kind": "tool", "tool": "resolve_turbulence_regime", "arguments": {"rytov_variance": 0.75}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "load_catalog", "arguments": {}},
        {"kind": "tool", "tool": "select_robust_configuration", "arguments": {"turbulence": "Moderate", "target_ber": 0.001, "max_ebn0_db": 25.0}},
        {"kind": "finish", "status": "success", "message": ""},
    ]


def recovery_actions(persistent: bool = False) -> list[dict[str, Any]]:
    actions = [
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 2.0}},
        {"kind": "tool", "tool": "resolve_turbulence_regime", "arguments": {"rytov_variance": 2.0}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
    ]
    if persistent:
        return actions + [{"kind": "finish", "status": "tool_error", "message": "persistent corruption"}]
    return actions + [
        {"kind": "tool", "tool": "load_catalog", "arguments": {}},
        {"kind": "tool", "tool": "select_robust_configuration", "arguments": {"turbulence": "Strong", "target_ber": 0.001, "max_ebn0_db": 30.0}},
        {"kind": "finish", "status": "success", "message": ""},
    ]


SCENARIOS = (
    ("normal", happy_actions, None, "success"),
    ("clarification", lambda: [{"kind": "finish", "status": "needs_clarification", "message": "need input"}], None, "needs_clarification"),
    ("recover_once", recovery_actions, "threshold_catalog_semantic_corruption_once", "success"),
    ("fail_closed", lambda: recovery_actions(True), "threshold_catalog_semantic_corruption_persistent", "tool_error"),
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction)))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5000)
    parser.add_argument(
        "--min-duration-seconds",
        type=float,
        default=0,
        help="Continue after --runs until this wall-clock duration is also reached.",
    )
    parser.add_argument("--report-every", type=int, default=500)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "qa" / "stability_latest.json")
    args = parser.parse_args()
    if args.runs < 1 or args.report_every < 1 or args.min_duration_seconds < 0:
        raise SystemExit("--runs/report-every must be positive; minimum duration cannot be negative")

    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    started = time.perf_counter()
    progress_path = output_path.with_suffix(".progress.jsonl")
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("", encoding="utf-8")
    tracemalloc.start()
    memory_before, _ = tracemalloc.get_traced_memory()
    # Keep a bounded sample for latency percentiles. Retaining every duration
    # would make the harness itself grow with run count and invalidate the
    # memory observation. Values are therefore explicitly reported as sampled.
    durations: deque[float] = deque(maxlen=512)
    outcomes = {"success": 0, "needs_clarification": 0, "tool_error": 0}
    expected_failures = 0
    unexpected = 0
    inconsistent = 0
    missing_trace = 0
    signatures: dict[str, tuple[Any, ...]] = {}
    checkpoint_count = 0
    last_checkpoint: dict[str, Any] | None = None

    run_number = 0
    while run_number < args.runs or (time.perf_counter() - started) < args.min_duration_seconds:
        run_number += 1
        name, factory, profile, expected = SCENARIOS[(run_number - 1) % len(SCENARIOS)]
        began = time.perf_counter()
        try:
            result = run_agent("offline stability QA", ScriptedPlanner(factory()), fault_profile=profile)
            durations.append((time.perf_counter() - began) * 1000)
            trace = result["trace"]
            signature = (result["status"], tuple((event["tool"], event["status"]) for event in trace))
            if result["status"] != expected:
                unexpected += 1
            outcomes[result["status"]] = outcomes.get(result["status"], 0) + 1
            if expected == "tool_error":
                expected_failures += 1
            if signatures.setdefault(name, signature) != signature:
                inconsistent += 1
            if any(not {"tool", "arguments", "status"} <= event.keys() for event in trace):
                missing_trace += 1
        except Exception:  # Report failures rather than silently discarding them.
            unexpected += 1
        if run_number % args.report_every == 0 or run_number == args.runs:
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
            last_checkpoint = {"completed_runs": run_number, "current_bytes": current, "peak_bytes": peak}
            with progress_path.open("a", encoding="utf-8") as progress_file:
                progress_file.write(json.dumps(last_checkpoint) + "\n")
            checkpoint_count += 1

    memory_after, memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    try:
        progress_reference = str(progress_path.relative_to(ROOT))
    except ValueError:
        # Tests and callers may intentionally write reports outside the repo.
        # Preserve a usable absolute reference instead of failing report creation.
        progress_reference = str(progress_path)
    report = {
        "scope": "offline deterministic Runtime scheduling only; excludes LLM/network and is not an end-to-end latency or SLA result",
        "requested_minimum_runs": args.runs,
        "requested_minimum_duration_seconds": args.min_duration_seconds,
        "runs": run_number,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "outcomes": outcomes,
        "expected_fail_closed": expected_failures,
        "unexpected_exceptions_or_results": unexpected,
        "inconsistent_results": inconsistent,
        "trace_missing_count": missing_trace,
        "latency_ms_sampled_last_512": {"p50": round(statistics.median(durations), 6), "p95": round(percentile(list(durations), 0.95), 6), "max": round(max(durations), 6)},
        "memory_bytes": {"before": memory_before, "after": memory_after, "peak": memory_peak, "delta": memory_after - memory_before},
        "checkpoint_progress_file": progress_reference,
        "checkpoint_count": checkpoint_count,
        "last_checkpoint": last_checkpoint,
        "passed": unexpected == 0 and inconsistent == 0 and missing_trace == 0,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
