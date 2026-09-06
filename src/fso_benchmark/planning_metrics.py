"""Planning-specific metrics for deterministic FSO trajectories."""

from __future__ import annotations

from statistics import fmean
from typing import Any

from .baseline import run_direct_baseline
from .rule_baseline import run_rule_baseline


def classify_failure(case: dict[str, Any], record: dict[str, Any]) -> str:
    """Assign one deterministic, mutually exclusive outcome category."""
    if record.get("passed") is True:
        return "passed"
    error = str(record.get("error") or "").lower()
    trace = record.get("trace") or []
    expected = case["expected"]
    if "invalid planner action" in error:
        return "invalid_planner_action"
    if "tool-call budget exhausted" in error:
        return "tool_budget_exhausted"
    if "provider" in error or "planner request failed" in error:
        return "provider_error"
    if expected["status"] == "success" and record.get("status") != "success":
        return "premature_stop"
    if record.get("status") != expected["status"]:
        return "wrong_status"
    if expected.get("requires_recovery") and not any(
        step.get("recovery") for step in trace
    ):
        return "recovery_contract_failed"
    required_statuses = set(expected.get("required_trace_statuses", []))
    if not required_statuses <= {step.get("status") for step in trace}:
        return "trace_contract_failed"
    if expected["status"] == "success":
        answer = record.get("answer") or {}
        selection = answer.get("selection") or {}
        if selection.get("configuration_id") != expected.get("configuration_id"):
            return "wrong_configuration"
    return "answer_contract_mismatch"


def score_planning_report(
    cases: list[dict[str, Any]], report: dict[str, Any]
) -> dict[str, Any]:
    case_by_id = {case["task_id"]: case for case in cases}
    constraint_violations = 0
    successful_plans = 0
    optimality_gaps: list[float] = []
    retry_cases = 0
    recovered_retry_cases = 0
    semantic_recovery_cases = 0
    recovered_semantic_cases = 0
    persistent_fault_cases = 0
    correct_persistent_stops = 0
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
            trace = record["trace"]
            had_error = any(
                step.get("tool") == "load_turbulence_catalog"
                and step.get("status") == "error"
                for step in trace
            )
            later_success = any(
                step.get("tool") == "load_turbulence_catalog"
                and step.get("status") == "success"
                for step in trace
            )
            if record["status"] == "success" and (
                any(
                    step.get("retry") and step["status"] == "success"
                    for step in trace
                )
                or (had_error and later_success)
            ):
                recovered_retry_cases += 1

        if inputs.get("injected_fault") == "threshold_catalog_semantic_corruption_once":
            semantic_recovery_cases += 1
            if record["status"] == "success" and any(
                step.get("recovery") == "clean_frozen_catalog"
                for step in record["trace"]
            ):
                recovered_semantic_cases += 1

        if inputs.get("injected_fault") in {
            "threshold_catalog_semantic_corruption_persistent",
            "threshold_catalog_unavailable",
        }:
            persistent_fault_cases += 1
            if record["passed"] and record["status"] == "tool_error":
                correct_persistent_stops += 1

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
                or (
                    "forbidden_codes" in inputs
                    and selection["code"] in inputs["forbidden_codes"]
                )
                or selection["target_ber"] > inputs["target_ber"]
            )
            constraint_violations += int(violated)
            optimality_gaps.append(float(selection["optimality_gap"]))

        successful_tools = [
            step["tool"] for step in record["trace"] if step["status"] == "success"
        ]
        duplicates = len(successful_tools) - len(set(successful_tools))
        if any(step.get("recovery") for step in record["trace"]):
            duplicates -= max(0, successful_tools.count("load_turbulence_catalog") - 1)
        duplicate_successful_steps += max(0, duplicates)

        record["failure_category"] = classify_failure(case, record)

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
        "semantic_recovery_cases": semantic_recovery_cases,
        "recovered_semantic_cases": recovered_semantic_cases,
        "semantic_recovery_rate": (
            recovered_semantic_cases / semantic_recovery_cases
            if semantic_recovery_cases
            else None
        ),
        "persistent_fault_cases": persistent_fault_cases,
        "correct_persistent_stops": correct_persistent_stops,
        "persistent_fault_stop_accuracy": (
            correct_persistent_stops / persistent_fault_cases
            if persistent_fault_cases
            else None
        ),
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
    categories: dict[str, int] = {}
    for record in report["results"]:
        category = record["failure_category"]
        categories[category] = categories.get(category, 0) + 1
    report["failure_analysis"] = {
        "failed_tasks": total - passed,
        "category_counts": dict(sorted(categories.items())),
    }
    return report


def run_planning_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return score_planning_report(cases, run_direct_baseline(cases))


def run_rule_planning_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return score_planning_report(cases, run_rule_baseline(cases))
