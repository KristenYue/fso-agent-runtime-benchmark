"""Framework-neutral execution boundary for the frozen FSO tools."""

from __future__ import annotations

from typing import Any

from .catalog import load_catalog, load_turbulence_catalog
from .faults import corrupt_threshold_ordering
from .tools import (
    characterize_turbulence,
    resolve_turbulence_regime,
    select_robust_configuration,
    validate_turbulence_catalog,
)


def execute_tool(
    tool: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    """Execute one allow-listed tool while retaining full data in runtime context."""
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
    """Bound planner context without exposing frozen catalog rows."""
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


def execute_tool_action(
    action: dict[str, Any],
    context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the public observation and updated private context for one action."""
    try:
        output, updated = execute_tool(action["tool"], action["arguments"], context)
        observation = {
            "tool": action["tool"],
            "arguments": action["arguments"],
            "status": "success",
            "output": compact_tool_output(action["tool"], output),
        }
        if (
            action["tool"] == "load_turbulence_catalog"
            and updated.get("fault_profile")
            == "threshold_catalog_semantic_corruption_once"
            and updated.get("threshold_catalog_attempts") == 2
        ):
            observation["recovery"] = "clean_frozen_catalog"
    except (KeyError, LookupError, TypeError, ValueError) as exc:
        updated = context
        # A failed catalog attempt still consumes an attempt and must affect retry behavior.
        if action["tool"] == "load_turbulence_catalog":
            updated = dict(context)
            updated["threshold_catalog_attempts"] = (
                context.get("threshold_catalog_attempts", 0) + 1
            )
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
    return observation, updated
