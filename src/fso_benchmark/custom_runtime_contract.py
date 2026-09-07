"""Validation helpers for the preregistered framework-free comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("artifacts/custom_runtime_contract_v1/contract.json")
RUNTIME_SOURCE_PATHS = (
    "src/fso_benchmark/agent_runtime.py",
    "src/fso_benchmark/tool_environment.py",
    "src/fso_benchmark/planner_contract.py",
    "src/fso_benchmark/model_planner.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate_contract(root: Path) -> dict[str, Any]:
    path = root / CONTRACT_PATH
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("status") != "preregistered_before_development_and_challenge":
        raise ValueError("custom Runtime contract is not preregistered")
    components = contract["frozen_components"]
    checks = {
        contract["datasets"]["development_path"]: contract["datasets"]["development_sha256"],
        contract["datasets"]["challenge_path"]: contract["datasets"]["challenge_sha256"],
        components["prompt_path"]: components["prompt_sha256"],
        components["action_schema_path"]: components["action_schema_sha256"],
        components["tools_path"]: components["tools_sha256"],
        components["catalog_loader_path"]: components["catalog_loader_sha256"],
        components["faults_path"]: components["faults_sha256"],
        components["answer_scorer_path"]: components["answer_scorer_sha256"],
        components["contracts_path"]: components["contracts_sha256"],
        components["scorer_path"]: components["scorer_sha256"],
        "data/turbulence_thresholds.json": components["threshold_catalog_sha256"],
        "data/configurations.json": components["configuration_catalog_sha256"],
        contract["dependencies"]["lock_path"]: contract["dependencies"]["lock_sha256"],
    }
    for relative, expected in checks.items():
        actual = sha256(root / relative)
        if actual != expected:
            raise ValueError(f"frozen component hash mismatch: {relative}")
    policy = contract["runtime_policy"]
    if policy.get("max_tool_calls") != 8 or policy.get("provider_retry_budget") != 1:
        raise ValueError("custom Runtime budget differs from preregistration")
    return contract


def runtime_source_hashes(root: Path) -> dict[str, str]:
    """Fingerprint the implementation selected by development for final comparison."""
    return {relative: sha256(root / relative) for relative in RUNTIME_SOURCE_PATHS}


def validate_model_environment(
    contract: dict[str, Any], *, provider: str, base_url: str, model: str
) -> None:
    expected = contract["model"]
    actual = {
        "provider": provider,
        "base_url": base_url.rstrip("/"),
        "snapshot_id": model,
    }
    for key, value in actual.items():
        if value != expected[key]:
            raise ValueError(f"model {key} differs from custom Runtime preregistration")
