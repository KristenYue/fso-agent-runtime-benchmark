"""Evaluation for the deterministic natural-language rule parser."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .baseline import execute_direct, matches_expected
from .rule_parser import parse_request


def run_rule_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        parsed = parse_request(case)
        parse_exact = parsed.operation == case["operation"] and parsed.inputs == case["inputs"]
        result = execute_direct(parsed)
        task_passed = matches_expected(result, case["expected"])
        record = {
            **result.to_dict(),
            "split": case["split"],
            "level": case["level"],
            "template_id": case["template_id"],
            "parsed_operation": parsed.operation,
            "parsed_inputs": parsed.inputs,
            "parse_exact": parse_exact,
            "passed": task_passed,
            "task_passed": task_passed,
        }
        records.append(record)
        grouped[(case["split"], case["level"])].append(record)

    def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        return {
            "total": total,
            "parse_exact": sum(row["parse_exact"] for row in rows),
            "parse_exact_rate": sum(row["parse_exact"] for row in rows) / total,
            "task_passed": sum(row["task_passed"] for row in rows),
            "task_pass_rate": sum(row["task_passed"] for row in rows) / total,
        }

    by_split_level = {
        f"{split}/{level}": metrics(rows)
        for (split, level), rows in sorted(grouped.items())
    }
    return {"summary": metrics(records), "by_split_level": by_split_level, "results": records}
