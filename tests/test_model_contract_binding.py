import json
from pathlib import Path

import pytest

from fso_benchmark.model_contract import (
    BOUND_STATUS,
    bind_model_identity,
    require_bound_model_contract,
)


def unbound_contract() -> dict:
    return {
        "contract": "langgraph_model_baseline_v1",
        "model": {"provider": "unconfigured", "snapshot_id": "unconfigured"},
        "status": "model_credentials_required",
    }


def test_binds_non_secret_model_identity_and_normalizes_url() -> None:
    bound = bind_model_identity(
        unbound_contract(),
        provider=" test-provider ",
        base_url="HTTPS://PROVIDER.INVALID/v1/",
        snapshot_id=" fixed-snapshot ",
    )
    assert bound["status"] == BOUND_STATUS
    assert bound["model"] == {
        "provider": "test-provider",
        "base_url": "https://provider.invalid/v1",
        "snapshot_id": "fixed-snapshot",
    }
    assert "api_key" not in json.dumps(bound).lower()


def test_refuses_rebinding_to_a_different_model() -> None:
    first = bind_model_identity(
        unbound_contract(),
        provider="provider-a",
        base_url="https://provider.invalid/v1",
        snapshot_id="snapshot-a",
    )
    with pytest.raises(ValueError, match="already bound"):
        bind_model_identity(
            first,
            provider="provider-b",
            base_url="https://provider.invalid/v1",
            snapshot_id="snapshot-b",
        )


def test_same_identity_requires_a_valid_bound_status() -> None:
    inconsistent = {
        "model": {
            "provider": "test-provider",
            "base_url": "https://provider.invalid/v1",
            "snapshot_id": "fixed-snapshot",
        },
        "status": "model_credentials_required",
    }
    with pytest.raises(ValueError, match="status is invalid"):
        bind_model_identity(
            inconsistent,
            provider="test-provider",
            base_url="https://provider.invalid/v1",
            snapshot_id="fixed-snapshot",
        )


def test_rejects_base_url_that_contains_credentials() -> None:
    with pytest.raises(ValueError, match="must not contain credentials"):
        bind_model_identity(
            unbound_contract(),
            provider="test-provider",
            base_url="https://user:password@provider.invalid/v1",
            snapshot_id="fixed-snapshot",
        )


def test_runner_identity_must_match_bound_contract(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    path.parent.mkdir(parents=True)
    bound = bind_model_identity(
        unbound_contract(),
        provider="test-provider",
        base_url="https://provider.invalid/v1",
        snapshot_id="fixed-snapshot",
    )
    path.write_text(json.dumps(bound), encoding="utf-8")
    with pytest.raises(ValueError, match="differs from frozen"):
        require_bound_model_contract(
            tmp_path,
            provider="test-provider",
            base_url="https://provider.invalid/v1",
            snapshot_id="different-snapshot",
        )
