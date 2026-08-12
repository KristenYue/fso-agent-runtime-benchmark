import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_development_runner_refuses_missing_credentials_without_artifact(tmp_path) -> None:
    env = dict(os.environ)
    for name in ("FSO_MODEL_BASE_URL", "FSO_MODEL_API_KEY", "FSO_MODEL_ID"):
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
