from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.agent_runtime import run_agent as run_custom_agent  # noqa: E402
from fso_benchmark.langgraph_agent import run_agent as run_langgraph_agent  # noqa: E402
from fso_benchmark.planner_contract import ScriptedPlanner  # noqa: E402


def successful_actions() -> list[dict]:
    return [
        {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_catalog","arguments":{}},
        {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Moderate","target_ber":0.001,"max_ebn0_db":25.0}},
        {"kind":"finish","status":"success","message":""},
    ]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def timed_run(runner) -> float:
    started = time.perf_counter_ns()
    result = runner("offline paired benchmark", ScriptedPlanner(successful_actions()))
    elapsed_us = (time.perf_counter_ns() - started) / 1000.0
    if result["status"] != "success" or len(result["trace"]) != 6:
        raise RuntimeError("benchmark runner did not produce the expected deterministic result")
    return elapsed_us


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean_us": statistics.mean(values),
        "median_us": statistics.median(values),
        "p95_us": percentile(values, 0.95),
        "stdev_us": statistics.stdev(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=500)
    parser.add_argument("--warmup-pairs", type=int, default=25)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "runtime_overhead_v1" / "results.json",
    )
    args = parser.parse_args()
    if args.pairs < 30 or args.warmup_pairs < 1:
        raise SystemExit("use at least 30 measured pairs and one warmup pair")

    for index in range(args.warmup_pairs):
        runners = (
            (run_langgraph_agent, run_custom_agent)
            if index % 2 == 0
            else (run_custom_agent, run_langgraph_agent)
        )
        for runner in runners:
            timed_run(runner)

    langgraph_us = []
    custom_us = []
    paired_custom_minus_langgraph_us = []
    for index in range(args.pairs):
        if index % 2 == 0:
            graph_elapsed = timed_run(run_langgraph_agent)
            custom_elapsed = timed_run(run_custom_agent)
        else:
            custom_elapsed = timed_run(run_custom_agent)
            graph_elapsed = timed_run(run_langgraph_agent)
        langgraph_us.append(graph_elapsed)
        custom_us.append(custom_elapsed)
        paired_custom_minus_langgraph_us.append(custom_elapsed - graph_elapsed)

    graph_summary = summarize(langgraph_us)
    custom_summary = summarize(custom_us)
    report = {
        "schema_version": "1.0",
        "experiment": "runtime_overhead_offline_paired_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "scheduler plus frozen deterministic local tool execution; no model or network",
        "method": {
            "pairs": args.pairs,
            "warmup_pairs": args.warmup_pairs,
            "order": "alternating within pairs",
            "clock": "time.perf_counter_ns",
            "request": "identical",
            "planner_actions": 7,
            "tool_calls": 6,
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "langgraph": graph_summary,
        "custom_runtime": custom_summary,
        "paired_difference": {
            "definition": "custom_runtime_us - langgraph_us",
            **summarize(paired_custom_minus_langgraph_us),
        },
        "median_speedup_ratio": (
            graph_summary["median_us"] / custom_summary["median_us"]
        ),
        "raw": {
            "langgraph_us": langgraph_us,
            "custom_runtime_us": custom_us,
            "paired_custom_minus_langgraph_us": paired_custom_minus_langgraph_us,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "pairs": args.pairs,
                "langgraph_median_us": graph_summary["median_us"],
                "custom_runtime_median_us": custom_summary["median_us"],
                "median_speedup_ratio": report["median_speedup_ratio"],
                "paired_median_difference_us": report["paired_difference"]["median_us"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
