from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.langgraph_baseline import run_offline_graph  # noqa: E402


def main() -> None:
    dataset_path = ROOT / "data" / "tasks_v2.json"
    dataset_bytes = dataset_path.read_bytes()
    payload = json.loads(dataset_bytes)
    cases = [
        case for case in payload["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]
    report = run_offline_graph(cases)
    output_dir = ROOT / "artifacts" / "langgraph_offline_smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    lock_bytes = (ROOT / "requirements-agents.lock").read_bytes()
    manifest = {
        "schema_version": "1.0",
        "experiment": "langgraph_offline_rule_smoke",
        "not_an_agent_model_baseline": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "source_git_sha": git_sha,
        "langgraph": importlib.metadata.version("langgraph"),
        "langchain_core": importlib.metadata.version("langchain-core"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "development_tasks": len(cases),
        "challenge_tasks_run": 0,
        "network_calls": 0,
        "model_calls": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
