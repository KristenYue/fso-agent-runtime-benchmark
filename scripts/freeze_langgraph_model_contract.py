from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    prompt_path = ROOT / "prompts" / "planner_v1.md"
    schema_path = ROOT / "schemas" / "planner_action_v1.json"
    lock_path = ROOT / "requirements-agents.lock"
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    contract = {
        "schema_version": "1.0",
        "contract": "langgraph_model_baseline_v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_sha": git_sha,
        "prompt": {"id": "planner_v1", "sha256": sha256(prompt_path)},
        "action_schema": {
            "id": "fso-planner-action-v1",
            "sha256": sha256(schema_path),
        },
        "dependencies": {
            "langgraph": importlib.metadata.version("langgraph"),
            "langchain_core": importlib.metadata.version("langchain-core"),
            "lock_sha256": sha256(lock_path),
        },
        "runtime_policy": {
            "max_tool_calls": 8,
            "planner_temperature": 0,
            "tool_retry_budget": 1,
            "challenge_runs_allowed": 1,
            "fault_profile_visible_to_planner": False,
            "catalog_observation_mode": "summary",
            "success_requires_optimizer_output": True,
            "threshold_validation_required": True,
        },
        "model": {
            "provider": "unconfigured",
            "snapshot_id": "unconfigured",
        },
        "status": "model_credentials_required",
    }
    output = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(contract, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
