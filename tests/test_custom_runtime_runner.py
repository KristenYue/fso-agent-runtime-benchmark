import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_development_runner_fails_closed_without_credentials(tmp_path: Path) -> None:
    env = dict(os.environ)
    for name in (
        "FSO_MODEL_PROVIDER",
        "FSO_MODEL_BASE_URL",
        "FSO_MODEL_API_KEY",
        "FSO_MODEL_ID",
    ):
        env.pop(name, None)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_custom_runtime_development.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "missing required model configuration" in completed.stderr
    assert not (tmp_path / "artifacts").exists()


def test_challenge_runner_fails_closed_without_configuration(tmp_path: Path) -> None:
    env = dict(os.environ)
    for name in (
        "FSO_MODEL_PROVIDER",
        "FSO_MODEL_BASE_URL",
        "FSO_MODEL_API_KEY",
        "FSO_MODEL_ID",
        "FSO_CUSTOM_RUNTIME_CHALLENGE_APPROVAL",
    ):
        env.pop(name, None)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_custom_runtime_challenge_once.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "model configuration is incomplete" in completed.stderr
    assert not (tmp_path / "artifacts").exists()
