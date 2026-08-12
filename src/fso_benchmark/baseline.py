"""Direct function/optimizer Oracle baseline."""

from __future__ import annotations

from typing import Any

from .catalog import load_catalog, load_turbulence_catalog
from .contracts import TaskResult, TaskSpec
from .tools import (
    calculate_ook_ber,
    characterize_turbulence,
    resolve_turbulence_regime,
    select_configuration,
    select_robust_configuration,
)


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
        elif task.operation == "plan_turbulence_aware_link":
            required_fields = ("rytov_variance", "target_ber", "max_ebn0_db")
            missing_fields = [field for field in required_fields if field not in task.inputs]
            if missing_fields:
                answer = {
                    "missing_fields": missing_fields,
                    "question": "请补充以下必要参数：" + "、".join(missing_fields),
                }
                trace.append(
                    {
                        "tool": "validate_required_inputs",
                        "status": "needs_clarification",
                        "missing_fields": missing_fields,
                    }
                )
                return TaskResult(
                    task.task_id,
                    "needs_clarification",
                    answer,
                    None,
                    tuple(trace),
                )
            turbulence_parameters = characterize_turbulence(task.inputs["rytov_variance"])
            trace.append({"tool": "characterize_turbulence", "status": "success"})
            regime = resolve_turbulence_regime(task.inputs["rytov_variance"])
            trace.append({"tool": "resolve_turbulence_regime", "status": "success"})
            fault_mode = task.inputs.get("injected_fault")
            if fault_mode == "threshold_catalog_timeout_once":
                trace.append(
                    {
                        "tool": "load_turbulence_catalog",
                        "status": "timeout",
                        "attempt": 1,
                    }
                )
                thresholds = load_turbulence_catalog()
                trace.append(
                    {
                        "tool": "load_turbulence_catalog",
                        "status": "success",
                        "attempt": 2,
                        "retry": True,
                        "rows": len(thresholds),
                    }
                )
            elif fault_mode == "threshold_catalog_unavailable":
                trace.extend(
                    [
                        {
                            "tool": "load_turbulence_catalog",
                            "status": "unavailable",
                            "attempt": 1,
                        },
                        {
                            "tool": "load_turbulence_catalog",
                            "status": "unavailable",
                            "attempt": 2,
                            "retry": True,
                        },
                    ]
                )
                return TaskResult(
                    task.task_id,
                    "tool_error",
                    None,
                    "threshold catalog unavailable after retry budget",
                    tuple(trace),
                )
            elif fault_mode is None:
                thresholds = load_turbulence_catalog()
                trace.append({"tool": "load_turbulence_catalog", "status": "success", "rows": len(thresholds)})
            else:
                raise ValueError("unsupported injected_fault")
            catalog = load_catalog()
            trace.append({"tool": "load_catalog", "status": "success", "rows": len(catalog)})
            optimizer_inputs = {
                key: value
                for key, value in task.inputs.items()
                if key not in {"rytov_variance", "injected_fault"}
            }
            selection = select_robust_configuration(
                thresholds,
                catalog,
                turbulence=regime["turbulence"],
                **optimizer_inputs,
            )
            trace.append({"tool": "select_robust_configuration", "status": "success"})
            answer = {
                "turbulence": {**regime, **turbulence_parameters},
                "selection": selection,
            }
        else:
            raise ValueError(f"unknown operation: {task.operation}")
        return TaskResult(task.task_id, "success", answer, None, tuple(trace))
    except KeyError as exc:
        trace.append({"tool": task.operation, "status": "invalid_input"})
        return TaskResult(task.task_id, "invalid_input", None, str(exc), tuple(trace))
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
