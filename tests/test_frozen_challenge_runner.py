import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_runner_module():
    path = ROOT / "scripts" / "run_langgraph_model_challenge_once.py"
    spec = importlib.util.spec_from_file_location("frozen_challenge_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_runner_fails_closed_without_approval() -> None:
    ledger = ROOT / "artifacts" / "langgraph_model_challenge" / "run_ledger.json"
    before = ledger.read_bytes() if ledger.exists() else None
    env = dict(os.environ)
    env.update(
        {
            "FSO_MODEL_PROVIDER": "test-provider",
            "FSO_MODEL_BASE_URL": "https://provider.invalid/v1",
            "FSO_MODEL_API_KEY": "test-only-secret",
            "FSO_MODEL_ID": "fixed-model",
        }
    )
    env.pop("FSO_FROZEN_CHALLENGE_APPROVAL", None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_langgraph_model_challenge_once.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "approval is missing" in result.stderr
    assert "test-only-secret" not in result.stderr
    after = ledger.read_bytes() if ledger.exists() else None
    assert after == before


def test_frozen_runner_rejects_contract_changed_after_development(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = load_runner_module()
    development_dir = tmp_path / "artifacts" / "langgraph_model_development"
    contract_dir = tmp_path / "artifacts" / "langgraph_model_contract_v1"
    development_dir.mkdir(parents=True)
    contract_dir.mkdir(parents=True)
    (development_dir / "manifest.json").write_text(
        json.dumps(
            {
                "model_provider": "test-provider",
                "model_id": "fixed-model",
                "base_url": "https://provider.invalid/v1",
                "contract_sha256": "stale-contract-hash",
            }
        ),
        encoding="utf-8",
    )
    (contract_dir / "contract.json").write_text(
        json.dumps(
            {
                "status": "model_bound_credentials_required",
                "model": {
                    "provider": "test-provider",
                    "base_url": "https://provider.invalid/v1",
                    "snapshot_id": "fixed-model",
                    "response_format_type": "json_schema",
                    "enable_thinking": False,
                    "local_action_schema_validation": True,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setenv("FSO_MODEL_PROVIDER", "test-provider")
    monkeypatch.setenv("FSO_MODEL_BASE_URL", "https://provider.invalid/v1")
    monkeypatch.setenv("FSO_MODEL_API_KEY", "test-only-secret")
    monkeypatch.setenv("FSO_MODEL_ID", "fixed-model")
    monkeypatch.setenv("FSO_FROZEN_CHALLENGE_APPROVAL", runner.APPROVAL_VALUE)

    with pytest.raises(SystemExit, match="contract differs from development manifest"):
        runner.require_final_configuration()
