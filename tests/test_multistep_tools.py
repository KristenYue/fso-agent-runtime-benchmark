import pytest

from fso_benchmark.baseline import execute_direct
from fso_benchmark.catalog import load_catalog, load_turbulence_catalog
from fso_benchmark.contracts import TaskSpec
from fso_benchmark.tools import resolve_turbulence_regime, select_robust_configuration


def test_resolve_turbulence_regime_only_accepts_validated_points() -> None:
    assert resolve_turbulence_regime(0.2)["turbulence"] == "Weak"
    assert resolve_turbulence_regime(0.75)["turbulence"] == "Moderate"
    assert resolve_turbulence_regime(2.0)["turbulence"] == "Strong"
    with pytest.raises(ValueError):
        resolve_turbulence_regime(1.0)


def test_optimizer_excludes_unbracketed_rs_thresholds() -> None:
    with pytest.raises(LookupError, match="unavailable_thresholds=2"):
        select_robust_configuration(
            load_turbulence_catalog(),
            load_catalog(),
            turbulence="Strong",
            target_ber=0.001,
            max_ebn0_db=40.0,
            allowed_codes=["RS"],
        )


def test_optimizer_minimizes_bandwidth_overhead_under_power_limit() -> None:
    selected = select_robust_configuration(
        load_turbulence_catalog(),
        load_catalog(),
        turbulence="Moderate",
        target_ber=0.001,
        max_ebn0_db=25.0,
    )
    assert selected["configuration_id"] == "LDPC-L64-D128"
    assert selected["optimality_gap"] == 0.0
    assert selected["verified_feasible_count"] == 4


def test_multistep_executor_records_five_successful_steps() -> None:
    task = TaskSpec(
        "multi-success",
        "L2",
        "plan_turbulence_aware_link",
        {"rytov_variance": 2.0, "target_ber": 0.001, "max_ebn0_db": 27.0},
    )
    result = execute_direct(task)
    assert result.status == "success"
    assert result.answer["selection"]["configuration_id"] == "LDPC-L64-D128"
    assert [step["tool"] for step in result.trace] == [
        "characterize_turbulence",
        "resolve_turbulence_regime",
        "load_turbulence_catalog",
        "load_catalog",
        "select_robust_configuration",
    ]


def test_multistep_executor_fails_closed_on_unvalidated_regime() -> None:
    task = TaskSpec(
        "multi-invalid",
        "L3",
        "plan_turbulence_aware_link",
        {"rytov_variance": 1.0, "target_ber": 0.001, "max_ebn0_db": 30.0},
    )
    result = execute_direct(task)
    assert result.status == "invalid_input"
    assert result.trace[-1]["status"] == "invalid_input"


def test_multistep_executor_reports_missing_required_field() -> None:
    task = TaskSpec(
        "multi-missing",
        "L3",
        "plan_turbulence_aware_link",
        {"target_ber": 0.001, "max_ebn0_db": 30.0},
    )
    result = execute_direct(task)
    assert result.status == "invalid_input"
    assert "rytov_variance" in result.error
