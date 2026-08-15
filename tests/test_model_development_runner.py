import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_langgraph_model_development import require_successful_compatibility_probe


ROOT = Path(__file__).resolve().parents[1]


def write_contract(root: Path) -> tuple[Path, dict]:
    contract = {
        "model": {
            "provider": "test-provider",
            "base_url": "https://provider.invalid/v1",
            "snapshot_id": "fixed-snapshot",
        }
    }
    path = root / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(contract), encoding="utf-8")
    return path, contract


def write_probe(root: Path, contract_path: Path, **overrides) -> dict:
    probe = {
        "passed": True,
        "error": None,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "provider": "test-provider",
        "base_url": "https://provider.invalid/v1",
        "snapshot_id": "fixed-snapshot",
        "credentials_recorded": False,
        "challenge_tasks_run": 0,
    }
    probe.update(overrides)
    path = root / "artifacts" / "langgraph_model_probe" / "probe.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(probe), encoding="utf-8")
    return probe


def test_development_runner_refuses_missing_credentials_without_artifact(tmp_path) -> None:
    env = dict(os.environ)
    for name in (
        "FSO_MODEL_PROVIDER",
        "FSO_MODEL_BASE_URL",
        "FSO_MODEL_API_KEY",
        "FSO_MODEL_ID",
    ):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_langgraph_model_development.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "missing required model configuration" in result.stderr
    assert "challenge_v1" not in result.stderr


def test_development_runner_requires_probe_for_current_contract(tmp_path: Path) -> None:
    _, contract = write_contract(tmp_path)
    with pytest.raises(ValueError, match="probe for current contract is missing"):
        require_successful_compatibility_probe(tmp_path, contract)


def test_development_runner_rejects_probe_for_old_contract(tmp_path: Path) -> None:
    path, contract = write_contract(tmp_path)
    write_probe(tmp_path, path, contract_sha256="0" * 64)
    with pytest.raises(ValueError, match="differs from current contract"):
        require_successful_compatibility_probe(tmp_path, contract)


def test_development_runner_accepts_clean_probe_for_current_contract(tmp_path: Path) -> None:
    path, contract = write_contract(tmp_path)
    expected = write_probe(tmp_path, path)
    assert require_successful_compatibility_probe(tmp_path, contract) == expected
