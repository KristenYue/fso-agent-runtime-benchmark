from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.baseline import run_direct_baseline  # noqa: E402


def main() -> None:
    task_path = ROOT / "data" / "tasks_seed.json"
    task_bytes = task_path.read_bytes()
    payload = json.loads(task_bytes)
    report = run_direct_baseline(payload["tasks"])
    output_dir = ROOT / "artifacts" / "direct_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_sha = "uncommitted"
    manifest = {
        "schema_version": "1.0",
        "baseline": "direct_oracle",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task_sha256": hashlib.sha256(task_bytes).hexdigest(),
        "git_sha": git_sha,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "network_calls": 0,
        "model_calls": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if report["summary"]["exact_match_rate"] != 1.0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

