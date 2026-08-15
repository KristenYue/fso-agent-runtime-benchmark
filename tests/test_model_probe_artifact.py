import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ITERATION_PATH = ROOT / "artifacts" / "langgraph_model_development_runs" / "iteration_01"
PROBE_PATH = ITERATION_PATH / "probe.json"
CONTRACT_PATH = ITERATION_PATH / "model_contract.json"


def test_archived_successful_probe_is_bound_to_its_contract_and_contains_no_credentials() -> None:
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert probe["passed"] is True
    assert probe["challenge_tasks_run"] == 0
    assert probe["credentials_recorded"] is False
    assert probe["contract_sha256"] == hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
    assert probe["provider"] == contract["model"]["provider"]
    assert probe["base_url"] == contract["model"]["base_url"]
    assert probe["snapshot_id"] == contract["model"]["snapshot_id"]
    assert probe["action"]["kind"] == probe["expected"]["kind"] == "finish"
    assert probe["action"]["status"] == probe["expected"]["status"] == "needs_clarification"
    assert probe["error"] is None

    serialized = json.dumps(probe).lower()
    for forbidden in ("api_key", "authorization", "bearer ", "access_token", "secret_key"):
        assert forbidden not in serialized


def test_successful_probe_has_one_complete_provider_telemetry_record() -> None:
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    telemetry = probe["model_telemetry"]

    assert len(telemetry) == 1
    call = telemetry[0]
    assert call["call_index"] == 1
    assert call["step"] == 0
    assert call["attempts"] == 1
    assert call["status_code"] == 200
    assert call["elapsed_ms"] > 0
    assert call["prompt_tokens"] > 0
    assert call["completion_tokens"] > 0
    assert call["total_tokens"] == call["prompt_tokens"] + call["completion_tokens"]
    assert call["provider_request_id"]
    assert call["idempotency_key"].startswith("fso-")
