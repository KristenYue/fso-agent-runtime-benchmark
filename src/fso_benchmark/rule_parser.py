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

    turbulence_request = bool(
        re.search(r"Rytov|sigma_R\^2|湍流方差", text, flags=re.IGNORECASE)
    )
    planning_request = bool(
        re.search(r"目标BER|BER\s*[≤=]|误码率", text, flags=re.IGNORECASE)
    ) and bool(
        turbulence_request
        or re.search(r"湍流感知链路|链路规划|选链路方案", text, flags=re.IGNORECASE)
    )

    if planning_request:
        operation = "plan_turbulence_aware_link"
        rytov = _search(
            [
                rf"Rytov方差(?:为|=)?\s*({NUMBER})",
                rf"sigma_R\^2\s*=\s*({NUMBER})",
                rf"湍流方差(?:取|为)?\s*({NUMBER})",
            ],
            text,
        )
        target = _search(
            [
                rf"目标BER(?:为|=)?\s*({NUMBER})",
                rf"BER\s*[≤=]\s*({NUMBER})",
                rf"误码率(?:不能超过|上限)\s*({NUMBER})",
            ],
            text,
        )
        power = _search(
            [
                rf"发射Eb/N0上限(?:为)?\s*({NUMBER})\s*dB",
                rf"功率预算\s*({NUMBER})\s*dB",
                rf"最多能给\s*({NUMBER})\s*dB",
            ],
            text,
        )
        if rytov is not None:
            inputs["rytov_variance"] = rytov
        if target is not None:
            inputs["target_ber"] = target
        if power is not None:
            inputs["max_ebn0_db"] = power

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
        if buffer_limit is not None:
            inputs["max_buffer_kib"] = buffer_limit
        if re.search(r"首次目录读取超时后重试一次|目录第一次超时就重试|目录若首调超时请重试", text):
            inputs["injected_fault"] = "threshold_catalog_timeout_once"
        elif re.search(r"目录持续不可用|目录两次都不可用|目录服务一直故障", text):
            inputs["injected_fault"] = "threshold_catalog_unavailable"
    elif turbulence_request:
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
