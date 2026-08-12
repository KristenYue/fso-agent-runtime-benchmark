import json
from pathlib import Path

import httpx
import pytest

from fso_benchmark.model_planner import OpenAICompatiblePlanner


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
    assert instance.telemetry[0]["provider_request_id"] == "req-1"


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
