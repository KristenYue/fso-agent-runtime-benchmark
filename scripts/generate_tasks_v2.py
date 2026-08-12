from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.generate_tasks_v1 import generate as generate_v1  # noqa: E402
from scripts.generate_tasks_v1 import expected_for  # noqa: E402
from fso_benchmark.dataset import validate_dataset  # noqa: E402


SPLITS = ("train", "dev", "test")


def planning_request(split: str, inputs: dict[str, Any]) -> tuple[str, str]:
    if split == "train":
        pieces = ["请完成湍流感知链路规划"]
        if "rytov_variance" in inputs:
            pieces.append(f"Rytov方差为 {inputs['rytov_variance']}")
        pieces.append(f"目标BER为 {inputs['target_ber']}")
        if "max_ebn0_db" in inputs:
            pieces.append(f"发射Eb/N0上限为 {inputs['max_ebn0_db']} dB")
        if "allowed_codes" in inputs:
            pieces.append(f"只允许{inputs['allowed_codes'][0]}编码")
        if "max_buffer_kib" in inputs:
            pieces.append(f"最大缓存为 {inputs['max_buffer_kib']} KiB")
        if inputs.get("injected_fault") == "threshold_catalog_timeout_once":
            pieces.append("首次目录读取超时后重试一次")
        elif inputs.get("injected_fault") == "threshold_catalog_unavailable":
            pieces.append("目录持续不可用")
        return "train-planning-formal", "，".join(pieces) + "。"
    if split == "dev":
        pieces = ["链路规划"]
        if "rytov_variance" in inputs:
            pieces.append(f"sigma_R^2={inputs['rytov_variance']}")
        pieces.append(f"BER≤{inputs['target_ber']}")
        if "max_ebn0_db" in inputs:
            pieces.append(f"功率预算 {inputs['max_ebn0_db']} dB")
        if "allowed_codes" in inputs:
            pieces.append(f"编码限定为{inputs['allowed_codes'][0]}")
        if "max_buffer_kib" in inputs:
            pieces.append(f"缓存上限 {inputs['max_buffer_kib']} KiB")
        if inputs.get("injected_fault") == "threshold_catalog_timeout_once":
            pieces.append("目录第一次超时就重试")
        elif inputs.get("injected_fault") == "threshold_catalog_unavailable":
            pieces.append("目录两次都不可用")
        return "dev-planning-compact", "；".join(pieces) + "。"
    pieces = ["帮我选链路方案"]
    if "rytov_variance" in inputs:
        pieces.append(f"湍流方差取 {inputs['rytov_variance']}")
    pieces.append(f"误码率不能超过 {inputs['target_ber']}")
    if "max_ebn0_db" in inputs:
        pieces.append(f"最多能给 {inputs['max_ebn0_db']} dB")
    if "allowed_codes" in inputs:
        pieces.append(f"只考虑{inputs['allowed_codes'][0]}")
    if "max_buffer_kib" in inputs:
        pieces.append(f"缓存最多 {inputs['max_buffer_kib']} KiB")
    if inputs.get("injected_fault") == "threshold_catalog_timeout_once":
        pieces.append("目录若首调超时请重试")
    elif inputs.get("injected_fault") == "threshold_catalog_unavailable":
        pieces.append("目录服务一直故障")
    return "test-planning-colloquial", "；".join(pieces) + "。"


def make_case(
    split: str,
    serial: int,
    level: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    task_id = f"{split}-planning-{serial:02d}"
    template_id, request = planning_request(split, inputs)
    expected = expected_for(task_id, level, "plan_turbulence_aware_link", inputs)
    return {
        "task_id": task_id,
        "split": split,
        "level": level,
        "template_id": template_id,
        "request": request,
        "operation": "plan_turbulence_aware_link",
        "inputs": inputs,
        "expected": expected,
        "must_reject": expected["status"] != "success",
        "passing_condition": "status_and_answer_contract_match",
    }


def planning_specs(split_index: int) -> list[tuple[str, dict[str, Any]]]:
    slack = split_index * 0.1
    missing_power_rytov = (0.2, 0.75, 2.0)[split_index]
    unavailable_rytov = (0.2, 0.75, 2.0)[split_index]
    return [
        ("L2", {"rytov_variance": 0.2, "target_ber": 0.001, "max_ebn0_db": 20.0 + slack}),
        ("L2", {"rytov_variance": 0.75, "target_ber": 0.001, "max_ebn0_db": 25.0 + slack}),
        ("L2", {"rytov_variance": 2.0, "target_ber": 0.001, "max_ebn0_db": 27.0 + slack}),
        ("L2", {"rytov_variance": 0.75, "target_ber": 0.001, "max_ebn0_db": 25.0 + slack, "allowed_codes": ["RS"]}),
        ("L2", {"rytov_variance": 0.75, "target_ber": 0.001, "max_ebn0_db": 30.0 + slack, "max_buffer_kib": 2.0 + slack}),
        ("L3", {"rytov_variance": 2.0, "target_ber": 0.001, "max_ebn0_db": 30.0 + slack, "injected_fault": "threshold_catalog_timeout_once"}),
        ("L3", {"rytov_variance": missing_power_rytov, "target_ber": 0.001}),
        ("L3", {"target_ber": 0.001, "max_ebn0_db": 22.0 + slack}),
        ("L3", {"rytov_variance": 2.0, "target_ber": 0.001, "max_ebn0_db": 40.0 + slack, "allowed_codes": ["RS"]}),
        ("L3", {"rytov_variance": unavailable_rytov, "target_ber": 0.001, "max_ebn0_db": 30.0 + slack, "injected_fault": "threshold_catalog_unavailable"}),
    ]


def generate() -> dict[str, Any]:
    payload = generate_v1()
    tasks = list(payload["tasks"])
    for split_index, split in enumerate(SPLITS):
        for serial, (level, inputs) in enumerate(planning_specs(split_index), start=1):
            tasks.append(make_case(split, serial, level, inputs))
    result = {
        "schema_version": "1.0",
        "dataset_version": "tasks-v2-development",
        "generator": "scripts/generate_tasks_v2.py",
        "tasks": tasks,
    }
    validate_dataset(result, minimum_tasks=150)
    return result


def main() -> None:
    payload = generate()
    output = ROOT / "data" / "tasks_v2.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['tasks'])} tasks to {output}")


if __name__ == "__main__":
    main()
