from pathlib import Path

import pytest

from fso_benchmark.recovery_contract import (
    load_and_validate_recovery_contract,
    validate_api_key,
)


ROOT = Path(__file__).resolve().parents[1]


def test_recovery_contract_preserves_zero_attempt_incident_and_runtime() -> None:
    contract = load_and_validate_recovery_contract(ROOT)
    assert contract["original_incident"]["provider_attempts"] == 0
    assert contract["recovery_preflight"]["on_any_failure"] == (
        "stop_before_new_ledger_and_request_user_input"
    )


@pytest.mark.parametrize("api_key", ["", "中文密钥", "sk-test key", "sk-test\n"])
def test_credential_preflight_rejects_unsafe_input(api_key: str) -> None:
    with pytest.raises(ValueError):
        validate_api_key(api_key)


def test_credential_preflight_accepts_ascii_without_whitespace() -> None:
    validate_api_key("sk-example_123-ABC")
