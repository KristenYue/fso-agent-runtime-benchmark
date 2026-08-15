"""Bind and verify the non-secret identity of the model baseline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


BOUND_STATUS = "model_bound_credentials_required"


def normalize_model_identity(
    provider: str, base_url: str, snapshot_id: str
) -> dict[str, str]:
    provider = provider.strip()
    snapshot_id = snapshot_id.strip()
    parsed = urlsplit(base_url.strip())
    if not provider or not snapshot_id:
        raise ValueError("model provider and snapshot ID must be non-empty")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("model base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("model base URL must not contain credentials, query, or fragment")
    normalized_url = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "")
    )
    return {
        "provider": provider,
        "base_url": normalized_url,
        "snapshot_id": snapshot_id,
    }


def bind_model_identity(
    contract: dict[str, Any], *, provider: str, base_url: str, snapshot_id: str
) -> dict[str, Any]:
    identity = normalize_model_identity(provider, base_url, snapshot_id)
    existing = contract.get("model")
    if not isinstance(existing, dict):
        raise ValueError("model contract has no model section")
    if existing.get("provider") != "unconfigured":
        if all(existing.get(key) == value for key, value in identity.items()):
            if contract.get("status") != BOUND_STATUS:
                raise ValueError("model contract identity is bound but status is invalid")
            return contract
        raise ValueError("model contract is already bound to a different identity")
    updated = dict(contract)
    updated["model"] = identity
    updated["status"] = BOUND_STATUS
    return updated


def require_bound_model_contract(
    root: Path, *, provider: str, base_url: str, snapshot_id: str
) -> dict[str, Any]:
    path = root / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    if not path.exists():
        raise ValueError("frozen model contract is missing")
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected = normalize_model_identity(provider, base_url, snapshot_id)
    if contract.get("status") != BOUND_STATUS:
        raise ValueError("frozen model contract is not bound to a model identity")
    actual = contract.get("model")
    if not isinstance(actual, dict) or any(
        actual.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("model configuration differs from frozen model contract")
    return contract
