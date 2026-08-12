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

from fso_benchmark.challenge_eval import (  # noqa: E402
    run_oracle_challenge,
    run_rule_challenge,
)
from fso_benchmark.dataset import load_dataset  # noqa: E402


def main() -> None:
    dataset_path = ROOT / "data" / "challenge_v1.json"
    dataset_bytes = dataset_path.read_bytes()
    payload = load_dataset(dataset_path, minimum_tasks=24)
    oracle = run_oracle_challenge(payload["tasks"])
    rule = run_rule_challenge(payload["tasks"])
    output_dir = ROOT / "artifacts" / "challenge_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "oracle_results.json").write_text(
        json.dumps(oracle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
        "experiment": "challenge_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "source_git_sha": git_sha,
        "frozen_rule_parser_source_commit": payload["frozen_rule_parser_source_commit"],
        "challenge_tasks": len(payload["tasks"]),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "network_calls": 0,
        "model_calls": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("ORACLE", json.dumps(oracle["summary"], ensure_ascii=False))
    print("RULE", json.dumps(rule["summary"], ensure_ascii=False))
    print(json.dumps(rule["by_challenge_family"], ensure_ascii=False, indent=2))
    if oracle["summary"]["exact_match_rate"] != 1.0:
        raise SystemExit("Oracle failed strict challenge contract")


if __name__ == "__main__":
    main()
