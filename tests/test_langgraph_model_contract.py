import json
from pathlib import Path

from fso_benchmark.langgraph_agent import ALLOWED_TOOLS


ROOT = Path(__file__).resolve().parents[1]


def test_json_schema_tool_allowlist_matches_runtime() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "planner_action_v1.json").read_text(encoding="utf-8")
    )
    schema_tools = set(schema["oneOf"][0]["properties"]["tool"]["enum"])
    assert schema_tools == ALLOWED_TOOLS


def test_prompt_states_critical_runtime_invariants() -> None:
    prompt = (ROOT / "prompts" / "planner_v1.md").read_text(encoding="utf-8")
    assert "Never calculate BER" in prompt
    assert "validate the turbulence threshold catalog" in prompt
    assert "only after `select_robust_configuration` succeeds" in prompt


def test_frozen_contract_records_hidden_environment_boundary() -> None:
    contract = json.loads(
        (
            ROOT
            / "artifacts"
            / "langgraph_model_contract_v1"
            / "contract.json"
        ).read_text(encoding="utf-8")
    )
    policy = contract["runtime_policy"]
    assert policy["fault_profile_visible_to_planner"] is False
    assert policy["catalog_observation_mode"] == "summary"
