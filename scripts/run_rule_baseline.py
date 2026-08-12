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

from fso_benchmark.dataset import load_dataset  # noqa: E402
from fso_benchmark.rule_baseline import run_rule_baseline  # noqa: E402


def main() -> None:
    dataset_path = ROOT / "data" / "tasks_v1.json"
    dataset_bytes = dataset_path.read_bytes()
    payload = load_dataset(dataset_path)
    report = run_rule_baseline(payload["tasks"])
    output_dir = ROOT / "artifacts" / "rule_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": "1.0",
        "baseline": "natural_language_rule_parser",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "source_git_sha": git_sha,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "network_calls": 0,
        "model_calls": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

