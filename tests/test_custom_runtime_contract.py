import json
from pathlib import Path

import pytest

from fso_benchmark.custom_runtime_contract import (
    load_and_validate_contract,
    validate_model_environment,
)


ROOT = Path(__file__).resolve().parents[1]


def test_preregistered_contract_matches_frozen_files() -> None:
    contract = load_and_validate_contract(ROOT)
    assert contract["primary_acceptance"] == {
        "strict_passed": 24,
        "strict_total": 24,
        "constraint_violations": 0,
    }


def test_contract_rejects_changed_frozen_file(tmp_path: Path) -> None:
    contract = json.loads(
        (ROOT / "artifacts/custom_runtime_contract_v1/contract.json").read_text(
            encoding="utf-8"
        )
    )
    path = tmp_path / "artifacts/custom_runtime_contract_v1/contract.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(contract), encoding="utf-8")
    for relative in (
        "data/tasks_v2.json",
        "data/challenge_v1.json",
        "prompts/planner_v1.md",
        "schemas/planner_action_v1.json",
        "src/fso_benchmark/tools.py",
        "src/fso_benchmark/planning_metrics.py",
        "data/turbulence_thresholds.json",
        "data/configurations.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="frozen component hash mismatch"):
        load_and_validate_contract(tmp_path)


def test_model_identity_must_match_preregistration() -> None:
    contract = load_and_validate_contract(ROOT)
    with pytest.raises(ValueError, match="snapshot_id"):
        validate_model_environment(
            contract,
            provider=contract["model"]["provider"],
            base_url=contract["model"]["base_url"],
            model="moving-alias",
        )
