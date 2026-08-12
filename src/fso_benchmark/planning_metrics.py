"""Planning-specific metrics for deterministic FSO trajectories."""

from __future__ import annotations

from statistics import fmean
from typing import Any

from .baseline import run_direct_baseline
from .rule_baseline import run_rule_baseline


def score_planning_report(
    cases: list[dict[str, Any]], report: dict[str, Any]
) -> dict[str, Any]:
    case_by_id = {case["task_id"]: case for case in cases}
    constraint_violations = 0
    successful_plans = 0
    optimality_gaps: list[float] = []
    retry_cases = 0
    recovered_retry_cases = 0
    expected_clarifications = 0
    correct_clarifications = 0
    premature_stops = 0
    duplicate_successful_steps = 0

    for record in report["results"]:
        case = case_by_id[record["task_id"]]
        inputs = case["inputs"]
        expected_status = case["expected"]["status"]
        record["split"] = case["split"]
        record["level"] = case["level"]

        if expected_status == "success" and record["status"] != "success":
            premature_stops += 1
        if expected_status == "needs_clarification":
            expected_clarifications += 1
            if record["status"] == "needs_clarification" and record["passed"]:
                correct_clarifications += 1

        if inputs.get("injected_fault") == "threshold_catalog_timeout_once":
            retry_cases += 1
            if record["status"] == "success" and any(
                step.get("retry") and step["status"] == "success"
                for step in record["trace"]
            ):
                recovered_retry_cases += 1

        if record["status"] == "success":
            successful_plans += 1
            selection = record["answer"]["selection"]
            violated = (
                selection["required_ebn0_db"] > inputs["max_ebn0_db"]
                or (
                    "max_buffer_kib" in inputs
                    and selection["buffer_kib"] > inputs["max_buffer_kib"]
                )
                or (
                    "allowed_codes" in inputs
                    and selection["code"] not in inputs["allowed_codes"]
                )
                or selection["target_ber"] > inputs["target_ber"]
            )
            constraint_violations += int(violated)
            optimality_gaps.append(float(selection["optimality_gap"]))

        successful_tools = [
            step["tool"] for step in record["trace"] if step["status"] == "success"
        ]
        duplicate_successful_steps += len(successful_tools) - len(set(successful_tools))

    total = len(cases)
    passed = sum(record["passed"] for record in report["results"])
    mean_tool_calls = fmean(len(record["trace"]) for record in report["results"])
    report["planning_metrics"] = {
        "total": total,
        "task_pass_rate": passed / total if total else 0.0,
        "successful_plans": successful_plans,
        "constraint_violations": constraint_violations,
        "constraint_violation_rate": (
            constraint_violations / successful_plans if successful_plans else 0.0
        ),
        "mean_optimality_gap": fmean(optimality_gaps) if optimality_gaps else None,
        "mean_tool_calls": mean_tool_calls,
        "retry_cases": retry_cases,
        "recovered_retry_cases": recovered_retry_cases,
        "retry_recovery_rate": recovered_retry_cases / retry_cases if retry_cases else None,
        "expected_clarifications": expected_clarifications,
        "correct_clarifications": correct_clarifications,
        "clarification_accuracy": (
            correct_clarifications / expected_clarifications
            if expected_clarifications
            else None
        ),
        "premature_stops": premature_stops,
        "duplicate_successful_steps": duplicate_successful_steps,
    }
    return report


def run_planning_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return score_planning_report(cases, run_direct_baseline(cases))


def run_rule_planning_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return score_planning_report(cases, run_rule_baseline(cases))
