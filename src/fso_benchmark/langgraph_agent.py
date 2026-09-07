"""Provider-neutral LangGraph planner/tool loop with deterministic guardrails."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from .catalog import load_catalog, load_turbulence_catalog
from .faults import corrupt_threshold_ordering, validate_fault_profile
from .planner_contract import PlannerRequestError
from .tools import (
    characterize_turbulence,
    resolve_turbulence_regime,
    select_robust_configuration,
    validate_turbulence_catalog,
)


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


class AgentState(TypedDict, total=False):
    request: str
    planner: Planner
    max_tool_calls: int
    tool_calls: int
    action: dict[str, Any]
    observations: list[dict[str, Any]]
    context: dict[str, Any]
    result: dict[str, Any]
    fault_profile: str | None
    fault_attempts: dict[str, int]


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


def _failure(status: str, error: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": status,
        "answer": None,
        "error": error,
        "trace": observations,
    }


def planner_node(state: AgentState) -> dict[str, Any]:
    observations = list(state.get("observations", []))
    tool_calls = state.get("tool_calls", 0)
    try:
        raw = state["planner"].decide(
            request=state["request"],
            observations=tuple(observations),
            step=tool_calls,
        )
        action = validate_planner_action(raw)
    except PlannerRequestError as exc:
        return {
            "action": {"kind": "terminal"},
            "result": _failure(
                "tool_error", f"planner request failed: {exc}", observations
            ),
        }
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "action": {"kind": "terminal"},
            "result": _failure("tool_error", f"invalid planner action: {exc}", observations),
        }

    if action["kind"] == "tool" and tool_calls >= state.get("max_tool_calls", 8):
        return {
            "action": {"kind": "terminal"},
            "result": _failure("tool_error", "tool-call budget exhausted", observations),
        }

    if action["kind"] == "finish":
        status = action["status"]
        context = state.get("context", {})
        if status == "success":
            selection = context.get("selection")
            if selection is None:
                result = _failure(
                    "tool_error",
                    "planner cannot finish successfully before optimizer output",
                    observations,
                )
            else:
                result = {
                    "status": "success",
                    "answer": {"selection": selection},
                    "error": None,
                    "trace": observations,
                }
        else:
            result = {
                "status": status,
                "answer": {"message": action["message"]} if action["message"] else None,
                "error": None if status == "needs_clarification" else action["message"],
                "trace": observations,
            }
        return {"action": {"kind": "terminal"}, "result": result}
    return {"action": action}


def _execute_tool(
    tool: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    updated = dict(context)
    if tool == "characterize_turbulence":
        output = characterize_turbulence(**arguments)
        updated["turbulence_parameters"] = output
    elif tool == "resolve_turbulence_regime":
        output = resolve_turbulence_regime(**arguments)
        updated["regime"] = output
    elif tool == "load_turbulence_catalog":
        if arguments:
            raise ValueError("load_turbulence_catalog takes no arguments")
        attempt = context.get("threshold_catalog_attempts", 0) + 1
        context["threshold_catalog_attempts"] = attempt
        updated["threshold_catalog_attempts"] = attempt
        profile = context.get("fault_profile")
        if profile == "threshold_catalog_timeout_once" and attempt == 1:
            raise ValueError("simulated threshold catalog timeout")
        if profile == "threshold_catalog_unavailable":
            raise ValueError("simulated threshold catalog unavailable")
        output = load_turbulence_catalog()
        if profile == "threshold_catalog_semantic_corruption_once" and attempt == 1:
            output = corrupt_threshold_ordering(output)
        elif profile == "threshold_catalog_semantic_corruption_persistent":
            output = corrupt_threshold_ordering(output)
        updated["thresholds"] = output
    elif tool == "validate_turbulence_catalog":
        if arguments:
            raise ValueError("validate_turbulence_catalog takes no arguments")
        if "thresholds" not in context:
            raise ValueError("threshold catalog must be loaded before validation")
        output = validate_turbulence_catalog(context["thresholds"])
        updated["thresholds_validated"] = True
    elif tool == "load_catalog":
        if arguments:
            raise ValueError("load_catalog takes no arguments")
        output = load_catalog()
        updated["configurations"] = output
    else:
        if not context.get("thresholds_validated"):
            raise ValueError("validated threshold catalog is required before optimization")
        if "configurations" not in context:
            raise ValueError("configuration catalog is required before optimization")
        output = select_robust_configuration(
            context["thresholds"], context["configurations"], **arguments
        )
        updated["selection"] = output
    return output, updated


def compact_tool_output(tool: str, output: Any) -> Any:
    """Keep full data in runtime context while bounding planner-visible observations."""
    if tool == "load_turbulence_catalog":
        return {
            "catalog": "turbulence_thresholds",
            "rows": len(output),
            "target_ber_values": sorted({row["target_ber"] for row in output}),
        }
    if tool == "load_catalog":
        return {
            "catalog": "configurations",
            "rows": len(output),
            "codes": sorted({row["code"] for row in output}),
            "coherence_bits": sorted({row["coherence_bits"] for row in output}),
        }
    return output


def tool_node(state: AgentState) -> dict[str, Any]:
    action = state["action"]
    observations = list(state.get("observations", []))
    context = dict(state.get("context", {}))
    try:
        output, context = _execute_tool(action["tool"], action["arguments"], context)
        observation = {
            "tool": action["tool"],
            "arguments": action["arguments"],
            "status": "success",
            "output": compact_tool_output(action["tool"], output),
        }
        if (
            action["tool"] == "load_turbulence_catalog"
            and context.get("fault_profile")
            == "threshold_catalog_semantic_corruption_once"
            and context.get("threshold_catalog_attempts") == 2
        ):
            observation["recovery"] = "clean_frozen_catalog"
    except (KeyError, LookupError, TypeError, ValueError) as exc:
        status = (
            "semantic_error"
            if action["tool"] == "validate_turbulence_catalog"
            else "error"
        )
        observation = {
            "tool": action["tool"],
            "arguments": action["arguments"],
            "status": status,
            "error": str(exc),
        }
    observations.append(observation)
    return {
        "observations": observations,
        "context": context,
        "tool_calls": state.get("tool_calls", 0) + 1,
    }


def route_after_planner(state: AgentState) -> Literal["tool", "end"]:
    return "end" if state["action"]["kind"] == "terminal" else "tool"


def build_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("tool", tool_node)
    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner", route_after_planner, {"tool": "tool", "end": END}
    )
    builder.add_edge("tool", "planner")
    return builder.compile()


def run_agent(
    request: str,
    planner: Planner,
    *,
    max_tool_calls: int = 8,
    fault_profile: str | None = None,
) -> dict[str, Any]:
    if max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be positive")
    validate_fault_profile(fault_profile)
    state = build_agent_graph().invoke(
        {
            "request": request,
            "planner": planner,
            "max_tool_calls": max_tool_calls,
            "tool_calls": 0,
            "observations": [],
            "context": {
                "fault_profile": fault_profile,
                "threshold_catalog_attempts": 0,
            },
        },
        {"recursion_limit": 2 * max_tool_calls + 4},
    )
    return state["result"]
