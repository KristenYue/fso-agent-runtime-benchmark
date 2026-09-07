import json
from pathlib import Path

import httpx
import pytest

from fso_benchmark.model_planner import OpenAICompatiblePlanner, calculate_token_cost
from fso_benchmark.langgraph_agent import run_agent


ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "prompts" / "planner_v1.md"
SCHEMA = ROOT / "schemas" / "planner_action_v1.json"


def response_body(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }


def planner(handler) -> OpenAICompatiblePlanner:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatiblePlanner(
        base_url="https://provider.invalid/v1",
        api_key="test-secret-key",
        model="fixed-model-snapshot",
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        client=client,
    )


def test_structured_planner_returns_validated_action_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-secret-key"
        payload = json.loads(request.content)
        assert payload["response_format"]["json_schema"]["strict"] is True
        return httpx.Response(
            200,
            headers={"x-request-id": "req-1"},
            json=response_body(
                json.dumps(
                    {"kind":"tool","tool":"load_catalog","arguments":{}},
                    separators=(",", ":"),
                )
            ),
        )

    instance = planner(handler)
    action = instance.decide(request="plan", observations=(), step=0)
    assert action == {"kind":"tool","tool":"load_catalog","arguments":{}}
    assert instance.usage_summary()["total_tokens"] == 20
    assert instance.usage_summary()["usage_complete"] is True
    assert instance.telemetry[0]["provider_request_id"] == "req-1"


def test_json_object_mode_disables_thinking_and_keeps_local_validation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["enable_thinking"] is False
        assert "json_schema" not in json.dumps(payload["response_format"])
        system_content = payload["messages"][0]["content"]
        assert "The exact action JSON Schema follows" in system_content
        assert '"additionalProperties":false' in system_content
        assert '"kind":{"const":"finish"}' in system_content
        return httpx.Response(
            200,
            json=response_body(
                '{"kind":"tool","tool":"read_private_file","arguments":{}}'
            ),
        )

    instance = OpenAICompatiblePlanner(
        base_url="https://provider.invalid/v1",
        api_key="test-secret-key",
        model="fixed-model-snapshot",
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        response_format_type="json_object",
        enable_thinking=False,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ValueError, match="not allowed"):
        instance.decide(request="unsafe", observations=(), step=0)


def test_retry_uses_same_idempotency_key() -> None:
    keys = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["idempotency-key"])
        if len(keys) == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json=response_body(
                '{"kind":"finish","status":"needs_clarification","message":"missing power"}'
            ),
        )

    instance = planner(handler)
    action = instance.decide(request="plan", observations=(), step=2)
    assert action["status"] == "needs_clarification"
    assert len(keys) == 2 and keys[0] == keys[1]
    assert instance.telemetry[0]["attempts"] == 2


def test_custom_runtime_can_use_a_distinct_idempotency_namespace() -> None:
    keys = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["idempotency-key"])
        return httpx.Response(
            200,
            json=response_body(
                '{"kind":"finish","status":"needs_clarification","message":"x"}'
            ),
        )

    instance = OpenAICompatiblePlanner(
        base_url="https://provider.invalid/v1",
        api_key="test-secret-key",
        model="fixed-model-snapshot",
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        idempotency_namespace="fso-custom-v1",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.decide(request="plan", observations=(), step=0)
    assert keys[0].startswith("fso-custom-v1-")


def test_bad_json_is_rejected_without_leaking_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_body("not-json"))

    instance = planner(handler)
    with pytest.raises(ValueError, match="not valid JSON") as error:
        instance.decide(request="plan", observations=(), step=0)
    assert "test-secret-key" not in str(error.value)


def test_provider_error_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error including private details")

    instance = planner(handler)
    with pytest.raises(ValueError, match="status 500") as error:
        instance.decide(request="plan", observations=(), step=0)
    assert "private details" not in str(error.value)
    assert "test-secret-key" not in str(error.value)


def test_invalid_tool_from_model_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=response_body(
                '{"kind":"tool","tool":"read_private_file","arguments":{}}'
            ),
        )

    instance = planner(handler)
    with pytest.raises(ValueError, match="not allowed"):
        instance.decide(request="unsafe", observations=(), step=0)


def test_cost_uses_dated_external_prices_without_rounding() -> None:
    cost = calculate_token_cost(
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        input_price_per_million=2.0,
        output_price_per_million=8.0,
    )
    assert cost == 6.0


def test_telemetry_records_are_copies_and_contain_no_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=response_body('{"kind":"finish","status":"needs_clarification","message":"x"}'),
        )

    instance = planner(handler)
    instance.decide(request="plan", observations=(), step=0)
    records = instance.telemetry_records()
    records[0]["attempts"] = 999
    assert instance.telemetry[0]["attempts"] == 1
    assert "test-secret-key" not in json.dumps(records)


def test_model_adapter_runs_semantic_recovery_without_seeing_fault_profile() -> None:
    actions = [
        {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":2.0}},
        {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":2.0}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_catalog","arguments":{}},
        {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Strong","target_ber":0.001,"max_ebn0_db":30.0}},
        {"kind":"finish","status":"success","message":""},
    ]
    payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        action = actions[len(payloads) - 1]
        return httpx.Response(200, json=response_body(json.dumps(action)))

    instance = planner(handler)
    result = run_agent(
        "recover from a semantic catalog error",
        instance,
        max_tool_calls=8,
        fault_profile="threshold_catalog_semantic_corruption_once",
    )
    assert result["status"] == "success"
    assert len(payloads) == 9
    serialized_payloads = json.dumps(payloads, ensure_ascii=False)
    assert "fault_profile" not in serialized_payloads
    assert "threshold_catalog_semantic_corruption_once" not in serialized_payloads
    assert "semantic_error" in serialized_payloads
    assert "clean_frozen_catalog" in serialized_payloads
