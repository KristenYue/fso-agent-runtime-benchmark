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
from fso_benchmark.planning_metrics import (  # noqa: E402
    run_planning_baseline,
    run_rule_planning_baseline,
)


def main() -> None:
    dataset_path = ROOT / "data" / "tasks_v2.json"
    dataset_bytes = dataset_path.read_bytes()
    payload = load_dataset(dataset_path, minimum_tasks=150)
    cases = [
        case for case in payload["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]
    direct = run_planning_baseline(cases)
    rule = run_rule_planning_baseline(cases)
    output_dir = ROOT / "artifacts" / "planning_baselines_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "direct_results.json").write_text(
        json.dumps(direct, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "rule_results.json").write_text(
        json.dumps(rule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": "1.0",
        "experiment": "planning_baselines_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "source_git_sha": git_sha,
        "planning_tasks": len(cases),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "network_calls": 0,
        "model_calls": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("DIRECT")
    print(json.dumps(direct["planning_metrics"], ensure_ascii=False, indent=2))
    print("RULE")
    print(json.dumps(rule["planning_metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
