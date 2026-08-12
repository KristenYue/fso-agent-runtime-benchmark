"""Frozen configuration catalog loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "data" / "configurations.json"
DEFAULT_TURBULENCE_CATALOG = (
    Path(__file__).resolve().parents[2] / "data" / "turbulence_thresholds.json"
)


def load_catalog(path: Path = DEFAULT_CATALOG) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0":
        raise ValueError("Unsupported catalog schema_version")
    rows = raw.get("configurations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Catalog must contain configurations")
    return rows


def load_turbulence_catalog(
    path: Path = DEFAULT_TURBULENCE_CATALOG,
) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0":
        raise ValueError("Unsupported turbulence catalog schema_version")
    rows = raw.get("thresholds")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Turbulence catalog must contain thresholds")
    return rows
