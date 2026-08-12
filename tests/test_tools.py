import math

import pytest

from fso_benchmark.catalog import load_catalog
from fso_benchmark.tools import calculate_ook_ber, characterize_turbulence, select_configuration


def test_characterize_turbulence_matches_validated_formula() -> None:
    result = characterize_turbulence(1.0)
    assert result["alpha"] == pytest.approx(4.393859025392147)
    assert result["beta"] == pytest.approx(2.5636319795036955)


@pytest.mark.parametrize("value", [0, -1, 11, math.inf, "1"])
def test_characterize_turbulence_rejects_out_of_domain(value) -> None:
    with pytest.raises(ValueError):
        characterize_turbulence(value)


def test_calculate_ook_ber_matches_q_function() -> None:
    assert calculate_ook_ber(10)["ber"] == pytest.approx(0.0007827011290012744)


def test_select_configuration_applies_constraints_before_objective() -> None:
    selected = select_configuration(
        load_catalog(), target_ber=1e-3, coherence_bits=64, max_latency_us=20
    )
    assert selected["configuration_id"] == "LDPC-L64-D32"


def test_select_configuration_reports_empty_feasible_set() -> None:
    with pytest.raises(LookupError):
        select_configuration(
            load_catalog(), target_ber=1e-3, coherence_bits=64,
            allowed_codes=["RS"], max_buffer_kib=0.1,
        )


def test_select_configuration_rejects_duplicate_codes() -> None:
    with pytest.raises(ValueError):
        select_configuration(
            load_catalog(), target_ber=1e-3, coherence_bits=64,
            allowed_codes=["RS", "RS"],
        )
