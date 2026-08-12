import json
from pathlib import Path

from scripts.generate_tasks_v1 import generate

from fso_benchmark.dataset import canonical_semantic_key, validate_dataset


ROOT = Path(__file__).resolve().parents[1]


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
    assert checked_in == generate()
