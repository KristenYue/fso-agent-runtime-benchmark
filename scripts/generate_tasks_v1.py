from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.baseline import execute_direct  # noqa: E402
from fso_benchmark.contracts import TaskSpec  # noqa: E402
from fso_benchmark.dataset import validate_dataset  # noqa: E402


SPLITS = ("train", "dev", "test")
TURBULENCE_VALUES = {
    "train": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    "dev": [0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6],
    "test": [1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4],
}
EBN0_VALUES = {
    "train": [-5.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0, 10.0],
    "dev": [-4.0, -1.0, 1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
    "test": [-3.0, -0.5, 1.5, 3.5, 5.5, 7.5, 9.5, 12.0],
}


def expected_for(task_id: str, level: str, operation: str, inputs: dict[str, Any]) -> dict[str, Any]:
    result = execute_direct(TaskSpec(task_id, level, operation, inputs))
    expected: dict[str, Any] = {"status": result.status}
    if result.status == "success" and result.answer is not None:
        if operation == "select_configuration":
            expected["configuration_id"] = result.answer["configuration_id"]
        else:
            expected["answer"] = result.answer
    return expected


def request_for(split: str, operation: str, inputs: dict[str, Any]) -> tuple[str, str]:
    if operation == "characterize_turbulence":
        value = inputs["rytov_variance"]
        if split == "train":
            return "train-turbulence-formal", f"请计算Rytov方差为 {value} 时的Gamma-Gamma参数。"
        if split == "dev":
            return "dev-turbulence-symbol", f"给定 sigma_R^2={value}，返回湍流alpha和beta。"
        return "test-turbulence-colloquial", f"湍流方差取 {value}，求 Gamma-Gamma 的两个形状参数。"
    if operation == "calculate_ook_ber":
        value = inputs["ebn0_db"]
        if split == "train":
            return "train-ber-formal", f"请计算Eb/N0为 {value} dB时的OOK理论BER。"
        if split == "dev":
            return "dev-ber-equation", f"OOK链路 Eb/N0={value} dB，理论BER是多少？"
        return "test-ber-colloquial", f"信噪比为 {value} dB，求 OOK 的理论误码率。"

    target = inputs["target_ber"]
    coherence = inputs["coherence_bits"]
    code = inputs.get("allowed_codes")
    code_name = code[0] if code else None
    if split == "train":
        pieces = [f"目标BER为 {target}", f"相干长度 {coherence} bit"]
        if code_name:
            pieces.append(f"只允许{code_name}编码")
        if "max_buffer_kib" in inputs:
            pieces.append(f"最大缓存为 {inputs['max_buffer_kib']} KiB")
        if "max_latency_us" in inputs:
            pieces.append(f"最大额外时延为 {inputs['max_latency_us']} us")
        return "train-config-formal", "，".join(pieces) + "，请选择配置。"
    if split == "dev":
        pieces = [f"链路要求 BER≤{target}", f"Lc={coherence} bit"]
        if code_name:
            pieces.append(f"编码限定为{code_name}")
        if "max_buffer_kib" in inputs:
            pieces.append(f"缓存上限 {inputs['max_buffer_kib']} KiB")
        if "max_latency_us" in inputs:
            pieces.append(f"额外时延上限 {inputs['max_latency_us']} us")
        return "dev-config-compact", "；".join(pieces) + "；选出方案。"
    pieces = [f"误码率上限 {target}", f"信道相干块 {coherence} 比特"]
    if code_name:
        pieces.append(f"只考虑{code_name}")
    if "max_buffer_kib" in inputs:
        pieces.append(f"缓存最多 {inputs['max_buffer_kib']} KiB")
    if "max_latency_us" in inputs:
        pieces.append(f"额外时延最多 {inputs['max_latency_us']} us")
    return "test-config-colloquial", "帮我选编码：" + "；".join(pieces) + "。"


def make_case(
    split: str,
    level: str,
    serial: int,
    operation: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    task_id = f"{split}-{level.lower()}-{serial:03d}"
    template_id, request = request_for(split, operation, inputs)
    expected = expected_for(task_id, level, operation, inputs)
    return {
        "task_id": task_id,
        "split": split,
        "level": level,
        "template_id": template_id,
        "request": request,
        "operation": operation,
        "inputs": inputs,
        "expected": expected,
        "must_reject": expected["status"] != "success",
        "passing_condition": "status_and_answer_contract_match",
    }


def l2_inputs(split_index: int) -> list[dict[str, Any]]:
    slack = split_index * 0.01
    return [
        {"target_ber": 0.001, "coherence_bits": 64, "max_latency_us": 0.1 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["LDPC"], "max_latency_us": 4.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["LDPC"], "max_latency_us": 16.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["LDPC"], "max_latency_us": 66.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["RS"], "max_buffer_kib": 0.3 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["RS"], "max_buffer_kib": 2.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["RS"], "max_latency_us": 64.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 64, "max_buffer_kib": 8.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "max_latency_us": 0.1 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["LDPC"], "max_latency_us": 4.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["LDPC"], "max_buffer_kib": 2.1 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["LDPC"], "max_buffer_kib": 8.1 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["RS"], "max_buffer_kib": 0.3 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["RS"], "max_buffer_kib": 2.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "allowed_codes": ["RS"], "max_buffer_kib": 8.0 + slack},
        {"target_ber": 0.001, "coherence_bits": 256, "max_buffer_kib": 32.0 + slack},
    ]


def l3_specs(split_index: int) -> list[tuple[str, dict[str, Any]]]:
    offset = split_index + 1
    return [
        ("characterize_turbulence", {"rytov_variance": -0.1 * offset}),
        ("characterize_turbulence", {"rytov_variance": 10.0 + 0.1 * offset}),
        ("calculate_ook_ber", {"ebn0_db": -20.0 - offset}),
        ("calculate_ook_ber", {"ebn0_db": 100.0 + offset}),
        ("select_configuration", {"target_ber": 10.0 ** (-4 - split_index), "coherence_bits": 64}),
        ("select_configuration", {"target_ber": 0.001, "coherence_bits": 65 + split_index}),
        ("select_configuration", {"target_ber": 0.001, "coherence_bits": 64, "allowed_codes": ["RS"], "max_buffer_kib": 0.01 * offset}),
        ("select_configuration", {"target_ber": 0.001, "coherence_bits": 256, "max_latency_us": -1.0 * offset}),
    ]


def generate() -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    for split_index, split in enumerate(SPLITS):
        serial = 1
        for value in TURBULENCE_VALUES[split]:
            tasks.append(make_case(split, "L1", serial, "characterize_turbulence", {"rytov_variance": value}))
            serial += 1
        for value in EBN0_VALUES[split]:
            tasks.append(make_case(split, "L1", serial, "calculate_ook_ber", {"ebn0_db": value}))
            serial += 1
        for inputs in l2_inputs(split_index):
            tasks.append(make_case(split, "L2", serial, "select_configuration", inputs))
            serial += 1
        for operation, inputs in l3_specs(split_index):
            tasks.append(make_case(split, "L3", serial, operation, inputs))
            serial += 1
    payload = {
        "schema_version": "1.0",
        "dataset_version": "tasks-v1-development",
        "generator": "scripts/generate_tasks_v1.py",
        "tasks": tasks,
    }
    validate_dataset(payload)
    return payload


def main() -> None:
    payload = generate()
    output = ROOT / "data" / "tasks_v1.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['tasks'])} tasks to {output}")


if __name__ == "__main__":
    main()

