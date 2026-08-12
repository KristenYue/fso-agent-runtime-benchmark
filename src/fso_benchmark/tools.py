"""Pure deterministic tools exposed to baselines and agents."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def characterize_turbulence(rytov_variance: Any) -> dict[str, float]:
    """Map plane-wave Rytov variance to Gamma-Gamma alpha and beta."""
    s = _finite_number(rytov_variance, "rytov_variance")
    if not 0.0 < s <= 10.0:
        raise ValueError("rytov_variance must be in (0, 10]")
    common = s ** (6.0 / 5.0)
    alpha = 1.0 / (
        math.exp(0.49 * s / (1.0 + 1.11 * common) ** (7.0 / 6.0)) - 1.0
    )
    beta = 1.0 / (
        math.exp(0.51 * s / (1.0 + 0.69 * common) ** (5.0 / 6.0)) - 1.0
    )
    return {"alpha": alpha, "beta": beta}


def calculate_ook_ber(ebn0_db: Any) -> dict[str, float]:
    """Return equal-probability OOK BER over AWGN: Q(sqrt(Eb/N0))."""
    db = _finite_number(ebn0_db, "ebn0_db")
    if not -20.0 <= db <= 100.0:
        raise ValueError("ebn0_db must be in [-20, 100]")
    linear = 10.0 ** (db / 10.0)
    ber = 0.5 * math.erfc(math.sqrt(linear) / math.sqrt(2.0))
    return {"ebn0_db": db, "ber": ber}


def select_configuration(
    configurations: Iterable[dict[str, Any]],
    *,
    target_ber: Any,
    coherence_bits: Any,
    allowed_codes: Any = None,
    max_buffer_kib: Any = None,
    max_latency_us: Any = None,
) -> dict[str, Any]:
    """Select minimum required Eb/N0 under explicit resource constraints."""
    target = _finite_number(target_ber, "target_ber")
    if not 0.0 < target < 0.5:
        raise ValueError("target_ber must be in (0, 0.5)")
    if target != 1e-3:
        raise ValueError("catalog currently supports target_ber=0.001 only")
    if isinstance(coherence_bits, bool) or coherence_bits not in {64, 256}:
        raise ValueError("coherence_bits must be 64 or 256")

    if allowed_codes is None:
        codes = {"RS", "LDPC"}
    elif not isinstance(allowed_codes, list) or not allowed_codes:
        raise ValueError("allowed_codes must be a non-empty list")
    else:
        codes = set(allowed_codes)
        if not codes <= {"RS", "LDPC"} or len(codes) != len(allowed_codes):
            raise ValueError("allowed_codes must contain unique RS/LDPC values")

    max_buffer = math.inf if max_buffer_kib is None else _finite_number(max_buffer_kib, "max_buffer_kib")
    max_latency = math.inf if max_latency_us is None else _finite_number(max_latency_us, "max_latency_us")
    if max_buffer < 0 or max_latency < 0:
        raise ValueError("resource limits must be non-negative")

    feasible = [
        row
        for row in configurations
        if row["target_ber"] == target
        and row["coherence_bits"] == coherence_bits
        and row["code"] in codes
        and row["buffer_kib"] <= max_buffer
        and row["additional_latency_us"] <= max_latency
    ]
    if not feasible:
        raise LookupError("no configuration satisfies all constraints")
    best = min(
        feasible,
        key=lambda row: (
            row["required_ebn0_db"],
            row["buffer_kib"],
            row["configuration_id"],
        ),
    )
    return dict(best)

