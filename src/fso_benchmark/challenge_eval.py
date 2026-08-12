"""Challenge-set evaluation with family-level reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from .baseline import run_direct_baseline
from .rule_baseline import run_rule_baseline


def _evaluate(
    cases: list[dict[str, Any]],
    runner: Callable[[list[dict[str, Any]]], dict[str, Any]],
) -> dict[str, Any]:
    report = runner(cases)
    case_by_id = {case["task_id"]: case for case in cases}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in report["results"]:
        family = case_by_id[record["task_id"]]["challenge_family"]
        record["challenge_family"] = family
        grouped[family].append(record)

    by_family = {}
    for family, records in sorted(grouped.items()):
        total = len(records)
        row = {
            "total": total,
            "task_passed": sum(record["passed"] for record in records),
            "task_pass_rate": sum(record["passed"] for record in records) / total,
        }
        if all("parse_exact" in record for record in records):
            row["parse_exact"] = sum(record["parse_exact"] for record in records)
            row["parse_exact_rate"] = row["parse_exact"] / total
        by_family[family] = row
    report["by_challenge_family"] = by_family
    return report


def run_oracle_challenge(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return _evaluate(cases, run_direct_baseline)


def run_rule_challenge(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return _evaluate(cases, run_rule_baseline)
