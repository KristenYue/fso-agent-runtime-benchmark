"""Framework-neutral planner action contract shared by agent runtimes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol


ALLOWED_TOOLS = {
    "characterize_turbulence",
    "resolve_turbulence_regime",
    "load_turbulence_catalog",
    "validate_turbulence_catalog",
    "load_catalog",
    "select_robust_configuration",
}
TOOL_ARGUMENT_CONTRACTS = {
    "characterize_turbulence": ({"rytov_variance"}, set()),
    "resolve_turbulence_regime": ({"rytov_variance"}, set()),
    "load_turbulence_catalog": (set(), set()),
    "validate_turbulence_catalog": (set(), set()),
    "load_catalog": (set(), set()),
    "select_robust_configuration": (
        {"turbulence", "target_ber", "max_ebn0_db"},
        {"allowed_codes", "forbidden_codes", "max_buffer_kib", "objective"},
    ),
}
FINAL_STATUSES = {
    "success",
    "needs_clarification",
    "invalid_input",
    "no_feasible_solution",
    "tool_error",
}


class Planner(Protocol):
    def decide(
        self,
        *,
        request: str,
        observations: Sequence[dict[str, Any]],
        step: int,
    ) -> dict[str, Any]: ...


class PlannerRequestError(ValueError):
    """A transport or provider-protocol failure, not an action-schema failure."""


@dataclass
class ScriptedPlanner:
    """Deterministic test double; not a model baseline."""

    actions: list[dict[str, Any]]
    position: int = 0

    def decide(
        self,
        *,
        request: str,
        observations: Sequence[dict[str, Any]],
        step: int,
    ) -> dict[str, Any]:
        del request, observations, step
        if self.position >= len(self.actions):
            return {"kind": "finish", "status": "tool_error", "message": "script exhausted"}
        action = self.actions[self.position]
        self.position += 1
        return action


def validate_planner_action(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("planner action must be an object")
    kind = raw.get("kind")
    if kind == "tool":
        if set(raw) != {"kind", "tool", "arguments"}:
            raise ValueError("tool action fields must be exactly kind/tool/arguments")
        tool = raw.get("tool")
        if tool not in ALLOWED_TOOLS:
            raise ValueError(f"tool is not allowed: {tool}")
        arguments = raw.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        required, optional = TOOL_ARGUMENT_CONTRACTS[tool]
        missing = required - set(arguments)
        unexpected = set(arguments) - required - optional
        if missing:
            raise ValueError(
                f"{tool} missing required arguments: {', '.join(sorted(missing))}"
            )
        if unexpected:
            raise ValueError(
                f"{tool} has unexpected arguments: {', '.join(sorted(unexpected))}"
            )
        return {"kind": "tool", "tool": tool, "arguments": arguments}
    if kind == "finish":
        if set(raw) != {"kind", "status", "message"}:
            raise ValueError("finish action fields must be exactly kind/status/message")
        status = raw.get("status")
        if status not in FINAL_STATUSES:
            raise ValueError("invalid final status")
        message = raw.get("message", "")
        if not isinstance(message, str):
            raise ValueError("finish message must be a string")
        return {"kind": "finish", "status": status, "message": message}
    raise ValueError("planner action kind must be tool or finish")
