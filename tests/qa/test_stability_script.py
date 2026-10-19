"""Regression coverage for the standalone long-running stability harness."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_stability_script_honours_duration_and_writes_progress(tmp_path: Path) -> None:
    output = tmp_path / "stability.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_stability_test.py"),
            "--runs", "4",
            "--min-duration-seconds", "0.05",
            "--report-every", "2",
            "--output", str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    progress = output.with_suffix(".progress.jsonl")
    assert report["runs"] >= 4
    assert report["duration_seconds"] >= 0.05
    assert report["checkpoint_count"] >= 2
    assert progress.exists()
    assert len(progress.read_text(encoding="utf-8").splitlines()) == report["checkpoint_count"]
