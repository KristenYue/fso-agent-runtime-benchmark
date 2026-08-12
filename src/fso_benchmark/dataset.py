"""Dataset loading and integrity checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_CASE_FIELDS = {
    "task_id",
    "split",
    "level",
    "template_id",
    "request",
    "operation",
    "inputs",
    "expected",
    "must_reject",
    "passing_condition",
}


def canonical_semantic_key(case: dict[str, Any]) -> str:
    payload = {"operation": case["operation"], "inputs": case["inputs"]}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_dataset(payload: dict[str, Any], *, minimum_tasks: int = 100) -> None:
    if payload.get("schema_version") != "1.0":
        raise ValueError("Unsupported dataset schema_version")
    cases = payload.get("tasks")
    if not isinstance(cases, list) or len(cases) < minimum_tasks:
        raise ValueError(f"Dataset must contain at least {minimum_tasks} tasks")

    ids: set[str] = set()
    semantic_keys: set[str] = set()
    templates_by_split: dict[str, set[str]] = {"train": set(), "dev": set(), "test": set()}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Every task must be an object")
        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            raise ValueError(f"Task missing fields: {sorted(missing)}")
        if case["split"] not in templates_by_split:
            raise ValueError("split must be train, dev, or test")
        if case["level"] not in {"L1", "L2", "L3"}:
            raise ValueError("level must be L1, L2, or L3")
        if not isinstance(case["request"], str) or not case["request"].strip():
            raise ValueError("request must be non-empty")
        if case["task_id"] in ids:
            raise ValueError(f"Duplicate task_id: {case['task_id']}")
        ids.add(case["task_id"])
        key = canonical_semantic_key(case)
        if key in semantic_keys:
            raise ValueError(f"Semantic duplicate: {case['task_id']}")
        semantic_keys.add(key)
        templates_by_split[case["split"]].add(case["template_id"])

    splits = list(templates_by_split)
    for index, left in enumerate(splits):
        for right in splits[index + 1 :]:
            overlap = templates_by_split[left] & templates_by_split[right]
            if overlap:
                raise ValueError(f"Template leakage between {left}/{right}: {sorted(overlap)}")


def load_dataset(path: Path, *, minimum_tasks: int = 100) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_dataset(payload, minimum_tasks=minimum_tasks)
    return payload

