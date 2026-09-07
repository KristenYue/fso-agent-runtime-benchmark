"""Small framework-free Agent Runtime implemented as an explicit state machine."""

from __future__ import annotations

from typing import Any

from .faults import validate_fault_profile
from .planner_contract import Planner, PlannerRequestError, validate_planner_action
from .tool_environment import execute_tool_action


def _failure(status: str, error: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": status, "answer": None, "error": error, "trace": observations}


def run_agent(
    request: str,
    planner: Planner,
    *,
    max_tool_calls: int = 8,
    fault_profile: str | None = None,
) -> dict[str, Any]:
    """Run Planner -> Tool until a validated finish action or a hard guardrail fires."""
    if max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be positive")
    validate_fault_profile(fault_profile)
    observations: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "fault_profile": fault_profile,
        "threshold_catalog_attempts": 0,
    }
    tool_calls = 0

    while True:
        try:
            raw = planner.decide(
                request=request,
                observations=tuple(observations),
                step=tool_calls,
            )
            action = validate_planner_action(raw)
        except PlannerRequestError as exc:
            return _failure(
                "tool_error", f"planner request failed: {exc}", observations
            )
        except (KeyError, TypeError, ValueError) as exc:
            return _failure("tool_error", f"invalid planner action: {exc}", observations)

        if action["kind"] == "finish":
            status = action["status"]
            if status == "success":
                selection = context.get("selection")
                if selection is None:
                    return _failure(
                        "tool_error",
                        "planner cannot finish successfully before optimizer output",
                        observations,
                    )
                return {
                    "status": "success",
                    "answer": {"selection": selection},
                    "error": None,
                    "trace": observations,
                }
            return {
                "status": status,
                "answer": {"message": action["message"]} if action["message"] else None,
                "error": None if status == "needs_clarification" else action["message"],
                "trace": observations,
            }

        if tool_calls >= max_tool_calls:
            return _failure("tool_error", "tool-call budget exhausted", observations)
        observation, context = execute_tool_action(action, context)
        observations.append(observation)
        tool_calls += 1
