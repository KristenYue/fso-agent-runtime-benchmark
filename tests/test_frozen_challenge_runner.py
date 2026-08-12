import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_runner_fails_closed_without_approval() -> None:
    ledger = ROOT / "artifacts" / "langgraph_model_challenge" / "run_ledger.json"
    before = ledger.read_bytes() if ledger.exists() else None
    env = dict(os.environ)
    env.update(
        {
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
