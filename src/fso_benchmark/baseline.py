"""Direct function/optimizer Oracle baseline."""

from __future__ import annotations

from typing import Any

from .catalog import load_catalog
from .contracts import TaskResult, TaskSpec
from .tools import calculate_ook_ber, characterize_turbulence, select_configuration


def execute_direct(task: TaskSpec) -> TaskResult:
    trace: list[dict[str, Any]] = []
    try:
        if task.operation == "characterize_turbulence":
            answer = characterize_turbulence(**task.inputs)
            trace.append({"tool": "characterize_turbulence", "status": "success"})
        elif task.operation == "calculate_ook_ber":
            answer = calculate_ook_ber(**task.inputs)
            trace.append({"tool": "calculate_ook_ber", "status": "success"})
        elif task.operation == "select_configuration":
            catalog = load_catalog()
            trace.append({"tool": "load_catalog", "status": "success", "rows": len(catalog)})
            answer = select_configuration(catalog, **task.inputs)
            trace.append({"tool": "select_configuration", "status": "success"})
        else:
            raise ValueError(f"unknown operation: {task.operation}")
        return TaskResult(task.task_id, "success", answer, None, tuple(trace))
    except LookupError as exc:
        trace.append({"tool": task.operation, "status": "no_feasible_solution"})
        return TaskResult(task.task_id, "no_feasible_solution", None, str(exc), tuple(trace))
    except (TypeError, ValueError) as exc:
        trace.append({"tool": task.operation, "status": "invalid_input"})
        return TaskResult(task.task_id, "invalid_input", None, str(exc), tuple(trace))


def matches_expected(result: TaskResult, expected: dict[str, Any]) -> bool:
    if result.status != expected["status"]:
        return False
    if "configuration_id" in expected:
        return bool(result.answer) and result.answer.get("configuration_id") == expected["configuration_id"]
    if "answer" in expected:
        return result.answer == expected["answer"]
    return True


def run_direct_baseline(cases: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for case in cases:
        task = TaskSpec.from_dict(case)
        result = execute_direct(task)
        passed = matches_expected(result, case["expected"])
        record = result.to_dict()
        record["passed"] = passed
        records.append(record)

    total = len(records)
    valid = [row for row in records if row["status"] == "success"]
    rejected = [row for row in records if row["status"] != "success"]
    return {
        "summary": {
            "total": total,
            "passed": sum(row["passed"] for row in records),
            "exact_match_rate": sum(row["passed"] for row in records) / total if total else 0.0,
            "successful_tasks": len(valid),
            "rejected_tasks": len(rejected),
            "mean_tool_calls": sum(len(row["trace"]) for row in records) / total if total else 0.0,
        },
        "results": records,
    }
