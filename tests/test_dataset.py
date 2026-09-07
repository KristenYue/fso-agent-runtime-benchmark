import json
from pathlib import Path

import pytest

from scripts.generate_tasks_v1 import generate

from fso_benchmark.dataset import canonical_semantic_key, validate_dataset


ROOT = Path(__file__).resolve().parents[1]


def assert_cross_platform_equal(checked_in, generated, path="root") -> None:
    """Compare generated fixtures while tolerating libm last-bit float drift."""
    if isinstance(checked_in, float) and isinstance(generated, (int, float)):
        assert generated == pytest.approx(checked_in, rel=1e-12, abs=1e-15), path
        return
    if isinstance(checked_in, dict) and isinstance(generated, dict):
        assert checked_in.keys() == generated.keys(), path
        for key in checked_in:
            assert_cross_platform_equal(checked_in[key], generated[key], f"{path}.{key}")
        return
    if isinstance(checked_in, list) and isinstance(generated, list):
        assert len(checked_in) == len(generated), path
        for index, (left, right) in enumerate(zip(checked_in, generated, strict=True)):
            assert_cross_platform_equal(left, right, f"{path}[{index}]")
        return
    assert checked_in == generated, path


def test_generated_dataset_has_120_unique_tasks() -> None:
    payload = generate()
    validate_dataset(payload)
    cases = payload["tasks"]
    assert len(cases) == 120
    assert len({case["task_id"] for case in cases}) == 120
    assert len({canonical_semantic_key(case) for case in cases}) == 120


def test_each_split_has_expected_level_distribution() -> None:
    cases = generate()["tasks"]
    for split in ("train", "dev", "test"):
        selected = [case for case in cases if case["split"] == split]
        assert len(selected) == 40
        assert sum(case["level"] == "L1" for case in selected) == 16
        assert sum(case["level"] == "L2" for case in selected) == 16
        assert sum(case["level"] == "L3" for case in selected) == 8


def test_template_ids_are_isolated_by_split() -> None:
    cases = generate()["tasks"]
    templates = {
        split: {case["template_id"] for case in cases if case["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert templates["train"].isdisjoint(templates["dev"])
    assert templates["train"].isdisjoint(templates["test"])
    assert templates["dev"].isdisjoint(templates["test"])


def test_checked_in_dataset_matches_generator() -> None:
    checked_in = json.loads((ROOT / "data" / "tasks_v1.json").read_text(encoding="utf-8"))
    assert_cross_platform_equal(checked_in, generate())
