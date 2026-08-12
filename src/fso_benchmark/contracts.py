"""Versioned task and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


TaskLevel = Literal["L1", "L2", "L3"]
ResultStatus = Literal["success", "invalid_input", "no_feasible_solution"]


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    level: TaskLevel
    operation: str
    inputs: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TaskSpec":
        required = {"task_id", "level", "operation", "inputs"}
        missing = required - raw.keys()
        if missing:
            raise ValueError(f"Task missing fields: {sorted(missing)}")
        if raw["level"] not in {"L1", "L2", "L3"}:
            raise ValueError("Task level must be L1, L2, or L3")
        if not isinstance(raw["inputs"], dict):
            raise ValueError("Task inputs must be an object")
        return cls(
            task_id=str(raw["task_id"]),
            level=raw["level"],
            operation=str(raw["operation"]),
            inputs=raw["inputs"],
        )


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: ResultStatus
    answer: dict[str, Any] | None
    error: str | None
    trace: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "answer": self.answer,
            "error": self.error,
            "trace": list(self.trace),
        }

