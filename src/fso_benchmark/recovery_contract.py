"""Validation for the transparent post-incident Challenge v1.1 protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .custom_runtime_contract import (
    load_and_validate_contract,
    runtime_source_hashes,
    sha256,
)


RECOVERY_CONTRACT_PATH = Path(
    "artifacts/custom_runtime_recovery_contract_v1_1/contract.json"
)


def validate_api_key(api_key: str) -> None:
    if not api_key:
        raise ValueError("API key is empty")
    if not api_key.isascii():
        raise ValueError("API key must contain ASCII characters only")
    if any(character.isspace() for character in api_key):
        raise ValueError("API key must not contain whitespace")


def load_and_validate_recovery_contract(root: Path) -> dict[str, Any]:
    contract = json.loads((root / RECOVERY_CONTRACT_PATH).read_text(encoding="utf-8"))
    if contract.get("status") != "preregistered_before_recovery_probe_and_model_call":
        raise ValueError("recovery contract is not preregistered")
    incident = contract["original_incident"]
    frozen = contract["frozen_inputs"]
    checks = {
        incident["ledger_path"]: incident["ledger_sha256"],
        incident["results_path"]: incident["results_sha256"],
        frozen["original_comparison_contract_path"]: frozen[
            "original_comparison_contract_sha256"
        ],
        frozen["development_manifest_path"]: frozen["development_manifest_sha256"],
        frozen["challenge_path"]: frozen["challenge_sha256"],
    }
    for relative, expected in checks.items():
        if sha256(root / relative) != expected:
            raise ValueError(f"recovery frozen artifact hash mismatch: {relative}")
    original = load_and_validate_contract(root)
    expected_model = contract["model"]
    for key in (
        "provider",
        "base_url",
        "snapshot_id",
        "response_format_type",
        "enable_thinking",
        "temperature",
    ):
        original_value = original["model"].get(key)
        if original_value != expected_model[key]:
            raise ValueError(f"recovery model setting differs from original: {key}")
    if runtime_source_hashes(root) != contract["runtime_source_sha256"]:
        raise ValueError("recovery Runtime source differs from development")
    raw = json.loads((root / incident["results_path"]).read_text(encoding="utf-8"))
    if raw["summary"].get("calls") != 0 or raw["summary"].get("attempts") != 0:
        raise ValueError("original incident was not a zero-provider-attempt failure")
    return contract
