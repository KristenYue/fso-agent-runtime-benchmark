"""Deterministic environment faults kept outside planner-visible inputs."""

from __future__ import annotations

from typing import Any


FAULT_PROFILES = {
    "threshold_catalog_timeout_once",
    "threshold_catalog_unavailable",
    "threshold_catalog_semantic_corruption_once",
    "threshold_catalog_semantic_corruption_persistent",
}


def validate_fault_profile(profile: str | None) -> str | None:
    if profile is not None and profile not in FAULT_PROFILES:
        raise ValueError("unsupported fault profile")
    return profile


def corrupt_threshold_ordering(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    corrupted = [dict(row) for row in rows]
    for row in corrupted:
        if (
            row["configuration_id"] == "LDPC-L64-D128"
            and row["turbulence"] == "Strong"
        ):
            row["required_ebn0_db"] = 10.0
            return corrupted
    raise ValueError("fault target configuration is missing")
