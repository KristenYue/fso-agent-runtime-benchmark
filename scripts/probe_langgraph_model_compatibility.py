from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.model_contract import require_bound_model_contract  # noqa: E402
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402


PROBE_REQUEST = (
    "Plan an FSO link, but no Rytov variance, target BER, or maximum Eb/N0 "
    "has been provided. Return the next JSON action."
)


def probe_passed(action: dict) -> bool:
    return (
        action.get("kind") == "finish"
        and action.get("status") == "needs_clarification"
    )


def main() -> None:
    provider = os.environ.get("FSO_MODEL_PROVIDER", "")
    base_url = os.environ.get("FSO_MODEL_BASE_URL", "")
    api_key = os.environ.get("FSO_MODEL_API_KEY", "")
    model = os.environ.get("FSO_MODEL_ID", "")
    if not all((provider, base_url, api_key, model)):
        raise SystemExit("model compatibility probe requires all four FSO_MODEL_* variables")
    try:
        contract = require_bound_model_contract(
            ROOT, provider=provider, base_url=base_url, snapshot_id=model
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"model contract validation failed: {exc}") from exc
    identity = contract["model"]
    planner = OpenAICompatiblePlanner(
        base_url=identity["base_url"],
        api_key=api_key,
        model=identity["snapshot_id"],
        prompt_path=ROOT / "prompts" / "planner_v1.md",
        schema_path=ROOT / "schemas" / "planner_action_v1.json",
        temperature=0.0,
        timeout_seconds=30.0,
        retry_budget=1,
        response_format_type=identity["response_format_type"],
        enable_thinking=identity["enable_thinking"],
    )
    action = planner.decide(request=PROBE_REQUEST, observations=(), step=0)
    passed = probe_passed(action)
    contract_path = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    report = {
        "schema_version": "1.0",
        "probe": "langgraph_model_compatibility_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": identity["provider"],
        "base_url": identity["base_url"],
        "snapshot_id": identity["snapshot_id"],
        "response_format_type": identity["response_format_type"],
        "enable_thinking": identity["enable_thinking"],
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "challenge_tasks_run": 0,
        "credentials_recorded": False,
        "expected": {"kind": "finish", "status": "needs_clarification"},
        "action": action,
        "passed": passed,
        "model_telemetry": planner.telemetry_records(),
    }
    output = ROOT / "artifacts" / "langgraph_model_probe" / "probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit("model compatibility probe returned a valid but incorrect action")


if __name__ == "__main__":
    main()
