"""Deterministic fixtures for the QA evidence suite; not frozen challenge data."""

from __future__ import annotations


def happy_actions() -> list[dict]:
    return [
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 0.75}},
        {"kind": "tool", "tool": "resolve_turbulence_regime", "arguments": {"rytov_variance": 0.75}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "load_catalog", "arguments": {}},
        {"kind": "tool", "tool": "select_robust_configuration", "arguments": {"turbulence": "Moderate", "target_ber": 0.001, "max_ebn0_db": 25.0}},
        {"kind": "finish", "status": "success", "message": ""},
    ]


def recovery_actions(*, persistent: bool = False) -> list[dict]:
    actions = [
        {"kind": "tool", "tool": "characterize_turbulence", "arguments": {"rytov_variance": 2.0}},
        {"kind": "tool", "tool": "resolve_turbulence_regime", "arguments": {"rytov_variance": 2.0}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "load_turbulence_catalog", "arguments": {}},
        {"kind": "tool", "tool": "validate_turbulence_catalog", "arguments": {}},
    ]
    if persistent:
        return actions + [{"kind": "finish", "status": "tool_error", "message": "persistent corruption"}]
    return actions + [
        {"kind": "tool", "tool": "load_catalog", "arguments": {}},
        {"kind": "tool", "tool": "select_robust_configuration", "arguments": {"turbulence": "Strong", "target_ber": 0.001, "max_ebn0_db": 30.0}},
        {"kind": "finish", "status": "success", "message": ""},
    ]
