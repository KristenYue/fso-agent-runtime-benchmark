"""Small deterministic natural-language parameter parser baseline."""

from __future__ import annotations

import re
from typing import Any

from .contracts import TaskSpec


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _search(patterns: list[str], text: str, *, integer: bool = False) -> int | float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1)) if integer else float(match.group(1))
    return None


def parse_request(case: dict[str, Any]) -> TaskSpec:
    """Parse only the request text; hidden operation/inputs are not consulted."""
    text = case["request"]
    inputs: dict[str, Any] = {}

    if re.search(r"Rytov|sigma_R\^2|湍流方差", text, flags=re.IGNORECASE):
        operation = "characterize_turbulence"
        value = _search(
            [
                rf"Rytov方差(?:为|=)?\s*({NUMBER})",
                rf"sigma_R\^2\s*=\s*({NUMBER})",
                rf"湍流方差(?:取|为)?\s*({NUMBER})",
            ],
            text,
        )
        if value is not None:
            inputs["rytov_variance"] = value
    elif re.search(r"Eb/N0|信噪比", text, flags=re.IGNORECASE):
        operation = "calculate_ook_ber"
        value = _search(
            [
                rf"Eb/N0(?:为|=)?\s*({NUMBER})\s*dB",
                rf"信噪比(?:为)?\s*({NUMBER})\s*dB",
            ],
            text,
        )
        if value is not None:
            inputs["ebn0_db"] = value
    else:
        operation = "select_configuration"
        target = _search(
            [
                rf"目标BER(?:为|=)?\s*({NUMBER})",
                rf"BER\s*[≤=]\s*({NUMBER})",
                rf"误码率上限\s*({NUMBER})",
            ],
            text,
        )
        coherence = _search(
            [
                r"相干长度\s*(?:为|=)?\s*(\d+)",
                r"Lc\s*=\s*(\d+)",
                r"信道相干块\s*(\d+)",
            ],
            text,
            integer=True,
        )
        if target is not None:
            inputs["target_ber"] = target
        if coherence is not None:
            inputs["coherence_bits"] = coherence

        rs_only = bool(re.search(r"只允许RS|编码限定为RS|只考虑RS", text, flags=re.IGNORECASE))
        ldpc_only = bool(re.search(r"只允许LDPC|编码限定为LDPC|只考虑LDPC", text, flags=re.IGNORECASE))
        if rs_only:
            inputs["allowed_codes"] = ["RS"]
        elif ldpc_only:
            inputs["allowed_codes"] = ["LDPC"]

        buffer_limit = _search(
            [
                rf"最大缓存为\s*({NUMBER})\s*KiB",
                rf"缓存上限\s*({NUMBER})\s*KiB",
                rf"缓存最多\s*({NUMBER})\s*KiB",
            ],
            text,
        )
        latency_limit = _search(
            [
                rf"最大额外时延为\s*({NUMBER})\s*us",
                rf"额外时延上限\s*({NUMBER})\s*us",
                rf"额外时延最多\s*({NUMBER})\s*us",
            ],
            text,
        )
        if buffer_limit is not None:
            inputs["max_buffer_kib"] = buffer_limit
        if latency_limit is not None:
            inputs["max_latency_us"] = latency_limit

    return TaskSpec(
        task_id=case["task_id"],
        level=case["level"],
        operation=operation,
        inputs=inputs,
    )

