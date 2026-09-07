from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.custom_runtime_contract import sha256  # noqa: E402
from fso_benchmark.model_planner import OpenAICompatiblePlanner  # noqa: E402
from fso_benchmark.recovery_contract import (  # noqa: E402
    RECOVERY_CONTRACT_PATH,
    validate_api_key,
)


PROBE_REQUEST = (
    "Plan an FSO link, but no Rytov variance, target BER, or maximum Eb/N0 "
    "has been provided. Return the next JSON action."
)


def main() -> None:
    provider = os.environ.get("FSO_MODEL_PROVIDER", "")
    base_url = os.environ.get("FSO_MODEL_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("FSO_MODEL_API_KEY", "")
    model = os.environ.get("FSO_MODEL_ID", "")
    output = ROOT / "artifacts" / "custom_runtime_recovery_probe_v1_1" / "probe.json"
    if output.exists():
        raise SystemExit("recovery credential probe artifact already exists")
    try:
        validate_api_key(api_key)
    except ValueError as exc:
        raise SystemExit(f"credential preflight failed: {exc}") from exc
    contract_path = ROOT / RECOVERY_CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") != "preregistered_before_recovery_probe_and_model_call":
        raise SystemExit("recovery protocol is not preregistered")
    expected = contract["model"]
    actual = {
        "provider": provider,
        "base_url": base_url,
        "snapshot_id": model,
    }
    for key, value in actual.items():
        if value != expected[key]:
            raise SystemExit(f"credential probe model {key} mismatch")

    planner = OpenAICompatiblePlanner(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt_path=ROOT / "prompts" / "planner_v1.md",
        schema_path=ROOT / "schemas" / "planner_action_v1.json",
        temperature=expected["temperature"],
        timeout_seconds=contract["runtime_policy"]["request_timeout_seconds"],
        retry_budget=0,
        response_format_type=expected["response_format_type"],
        enable_thinking=expected["enable_thinking"],
        idempotency_namespace="fso-custom-v1-1-probe",
    )
    action = None
    error = None
    try:
        action = planner.decide(request=PROBE_REQUEST, observations=(), step=0)
    except Exception as exc:  # Save a sanitized failure artifact and stop before Challenge.
        error = {"type": type(exc).__name__, "message": str(exc)}
    telemetry = planner.telemetry_records()
    passed = (
        isinstance(action, dict)
        and action.get("kind") == "finish"
        and action.get("status") == "needs_clarification"
        and error is None
        and len(telemetry) == 1
        and telemetry[0].get("attempts") == 1
        and telemetry[0].get("status_code") == 200
    )
    report = {
        "schema_version": "1.0",
        "probe": "custom_runtime_recovery_credential_v1_1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "base_url": base_url,
        "snapshot_id": model,
        "recovery_contract_sha256": sha256(contract_path),
        "challenge_tasks_loaded": 0,
        "challenge_tasks_run": 0,
        "credentials_recorded": False,
        "expected": {"kind": "finish", "status": "needs_clarification"},
        "action": action,
        "error": error,
        "passed": passed,
        "model_telemetry": telemetry,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit("recovery credential probe failed; Challenge was not started")


if __name__ == "__main__":
    main()
