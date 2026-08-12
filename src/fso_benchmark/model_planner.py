"""OpenAI-compatible structured planner with bounded retries and telemetry."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

import httpx

from .langgraph_agent import validate_planner_action


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenAICompatiblePlanner:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        prompt_path: Path,
        schema_path: Path,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        retry_budget: int = 1,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("base_url must be HTTP(S)")
        if not api_key:
            raise ValueError("api_key is required")
        if not model:
            raise ValueError("model is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if retry_budget not in {0, 1}:
            raise ValueError("retry_budget must be 0 or 1")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.system_prompt = prompt_path.read_text(encoding="utf-8")
        self.action_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.retry_budget = retry_budget
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.telemetry: list[dict[str, Any]] = []

    def _idempotency_key(self, request: str, step: int) -> str:
        material = f"{self.model}\0{step}\0{request}".encode("utf-8")
        return "fso-" + hashlib.sha256(material).hexdigest()[:32]

    def _payload(
        self,
        *,
        request: str,
        observations: Sequence[dict[str, Any]],
        step: int,
    ) -> dict[str, Any]:
        state_message = {
            "request": request,
            "step": step,
            "observations": list(observations),
        }
        return {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(state_message, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "fso_planner_action_v1",
                    "strict": True,
                    "schema": self.action_schema,
                },
            },
        }

    def decide(
        self,
        *,
        request: str,
        observations: Sequence[dict[str, Any]],
        step: int,
    ) -> dict[str, Any]:
        payload = self._payload(request=request, observations=observations, step=step)
        idempotency_key = self._idempotency_key(request, step)
        attempts = 0
        started = time.perf_counter()
        response: httpx.Response | None = None
        last_error: str | None = None
        for attempt in range(1, self.retry_budget + 2):
            attempts = attempt
            try:
                response = self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Idempotency-Key": idempotency_key,
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException:
                last_error = "planner request timed out"
                if attempt <= self.retry_budget:
                    continue
                break
            if response.status_code in RETRYABLE_STATUS_CODES and attempt <= self.retry_budget:
                last_error = f"retryable provider status {response.status_code}"
                continue
            break

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        usage: dict[str, Any] = {}
        provider_request_id = None
        if response is not None:
            provider_request_id = response.headers.get("x-request-id")
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("usage"), dict):
                    usage = body["usage"]
            except ValueError:
                body = None
        else:
            body = None
        self.telemetry.append(
            {
                "call_index": len(self.telemetry) + 1,
                "step": step,
                "attempts": attempts,
                "elapsed_ms": elapsed_ms,
                "status_code": response.status_code if response is not None else None,
                "provider_request_id": provider_request_id,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "idempotency_key": idempotency_key,
            }
        )

        if response is None:
            raise ValueError(last_error or "planner request failed")
        if response.status_code >= 400:
            raise ValueError(f"provider request failed with status {response.status_code}")
        if not isinstance(body, dict):
            raise ValueError("provider returned non-JSON response")
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("provider response missing message content") from exc
        if not isinstance(content, str):
            raise ValueError("provider message content must be a JSON string")
        try:
            action = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("provider message content is not valid JSON") from exc
        return validate_planner_action(action)

    def usage_summary(self) -> dict[str, Any]:
        return {
            "calls": len(self.telemetry),
            "attempts": sum(row["attempts"] for row in self.telemetry),
            "prompt_tokens": sum(row["prompt_tokens"] or 0 for row in self.telemetry),
            "completion_tokens": sum(row["completion_tokens"] or 0 for row in self.telemetry),
            "total_tokens": sum(row["total_tokens"] or 0 for row in self.telemetry),
            "elapsed_ms": sum(row["elapsed_ms"] for row in self.telemetry),
        }
