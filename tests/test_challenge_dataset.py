import json
from collections import Counter
from pathlib import Path

from scripts.build_challenge_v1 import build

from fso_benchmark.baseline import run_direct_baseline
from fso_benchmark.rule_baseline import run_rule_baseline


ROOT = Path(__file__).resolve().parents[1]


def test_challenge_has_24_balanced_unique_templates() -> None:
    payload = build()
    assert len(payload["tasks"]) == 24
    counts = Counter(case["challenge_family"] for case in payload["tasks"])
    assert set(counts.values()) == {4}
    assert len({case["template_id"] for case in payload["tasks"]}) == 24


def test_checked_in_challenge_matches_curated_builder() -> None:
    checked_in = json.loads((ROOT / "data" / "challenge_v1.json").read_text(encoding="utf-8"))
    assert checked_in == build()


def test_oracle_satisfies_strict_challenge_contract() -> None:
    report = run_direct_baseline(build()["tasks"])
    assert report["summary"]["exact_match_rate"] == 1.0


def test_frozen_rule_parser_has_measurable_challenge_boundary() -> None:
    report = run_rule_baseline(build()["tasks"])
    assert report["summary"]["parse_exact_rate"] < 1.0
    assert report["summary"]["task_pass_rate"] < 1.0
