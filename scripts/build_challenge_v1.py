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


def case(
    number: int,
    family: str,
    request: str,
    inputs: dict[str, Any],
    *,
    required_trace_statuses: list[str] | None = None,
    requires_recovery: bool = False,
) -> dict[str, Any]:
    task_id = f"challenge-{number:02d}"
    task = TaskSpec(task_id, "L3", "plan_turbulence_aware_link", inputs)
    result = execute_direct(task)
    expected: dict[str, Any] = {"status": result.status}
    if result.status == "success":
        expected["configuration_id"] = result.answer["selection"]["configuration_id"]
    if required_trace_statuses:
        expected["required_trace_statuses"] = required_trace_statuses
    if requires_recovery:
        expected["requires_recovery"] = True
    return {
        "task_id": task_id,
        "split": "test",
        "level": "L3",
        "template_id": f"challenge-{family}-{number:02d}",
        "challenge_family": family,
        "request": request,
        "operation": "plan_turbulence_aware_link",
        "inputs": inputs,
        "expected": expected,
        "must_reject": result.status != "success",
        "passing_condition": "strict_status_choice_and_required_trace_contract",
    }


def build() -> dict[str, Any]:
    rows = [
        case(1, "cross_sentence", "先按中等湍流考虑链路。Rytov 取0.75。误码率必须压到1e-3，系统最多提供25分贝的Eb/N0。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":25.0}),
        case(2, "cross_sentence", "我要规划强湍流链路。sigma的平方是2。BER不能高于0.001。功率预算是27 dB。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":27.0}),
        case(3, "cross_sentence", "弱湍流场景，方差0.2。目标误码率千分之一，Eb/N0封顶20 dB。", {"rytov_variance":0.2,"target_ber":0.001,"max_ebn0_db":20.0}),
        case(4, "cross_sentence", "链路要在中等湍流下工作；湍流指标0.75。请满足BER千分之一和25 dB上限，同时缓存不得超过2 KiB。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":25.0,"max_buffer_kib":2.0}),
        case(5, "implicit_units", "做弱湍流链路规划：Rytov方差0.2，BER上限千分之一，功率只有二十点一分贝。", {"rytov_variance":0.2,"target_ber":0.001,"max_ebn0_db":20.1}),
        case(6, "implicit_units", "强湍流，sigma_R平方等于2；误码率上限10的负三次方；可用信噪比二十七点一分贝。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":27.1}),
        case(7, "implicit_units", "中等湍流链路：方差四分之三，BER千分之一，功率预算二十五点一分贝。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":25.1}),
        case(8, "implicit_units", "请选链路。Rytov=0.75，BER=0.1%，Eb/N0最多25.2 dB。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":25.2}),
        case(9, "constraint_conflict", "规划链路：Rytov方差为0.75，目标BER为0.001，发射Eb/N0上限为30 dB。只允许RS，但安全策略同时禁止RS。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":30.0,"allowed_codes":["RS"],"forbidden_codes":["RS"]}),
        case(10, "constraint_conflict", "强湍流链路，方差2，BER不超过1e-3，功率30 dB。限定LDPC，后文又要求不要使用LDPC。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":30.0,"allowed_codes":["LDPC"],"forbidden_codes":["LDPC"]}),
        case(11, "constraint_conflict", "弱湍流方案：sigma_R^2=0.2，BER≤0.001，预算20 dB。只考虑RS；合规条款排除RS。", {"rytov_variance":0.2,"target_ber":0.001,"max_ebn0_db":20.0,"allowed_codes":["RS"],"forbidden_codes":["RS"]}),
        case(12, "constraint_conflict", "中等湍流，0.75；目标BER千分之一；预算30 dB。编码限定为LDPC，不过设备清单明确禁用LDPC。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":30.0,"allowed_codes":["LDPC"],"forbidden_codes":["LDPC"]}),
        case(13, "semantic_recovery", "Rytov方差为2，目标BER为0.001，发射Eb/N0上限为30 dB。阈值目录首个响应数值自洽性错误，检测后改用冻结副本。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":30.0,"injected_fault":"threshold_catalog_semantic_corruption_once"}, required_trace_statuses=["semantic_error"], requires_recovery=True),
        case(14, "semantic_recovery", "规划中等湍流链路，方差0.75，BER上限1e-3，功率30 dB。若目录把强湍流门限写得更低，识别后重载可信目录。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":30.0,"injected_fault":"threshold_catalog_semantic_corruption_once"}, required_trace_statuses=["semantic_error"], requires_recovery=True),
        case(15, "semantic_recovery", "弱湍流0.2，BER≤0.001，功率20 dB。目录第一次返回违反湍流单调性的值，请校验并恢复。", {"rytov_variance":0.2,"target_ber":0.001,"max_ebn0_db":20.0,"injected_fault":"threshold_catalog_semantic_corruption_once"}, required_trace_statuses=["semantic_error"], requires_recovery=True),
        case(16, "semantic_recovery", "强湍流链路，Rytov=2，目标千分之一，预算30.1 dB。语义校验首次失败后允许读取冻结版本。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":30.1,"injected_fault":"threshold_catalog_semantic_corruption_once"}, required_trace_statuses=["semantic_error"], requires_recovery=True),
        case(17, "semantic_persistent", "Rytov方差2，BER上限0.001，功率30 dB。目录连续两次都违反湍流门限排序，停止并报工具错误。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":30.0,"injected_fault":"threshold_catalog_semantic_corruption_persistent"}, required_trace_statuses=["semantic_error"]),
        case(18, "semantic_persistent", "中等湍流0.75，目标1e-3，预算30 dB。两次目录响应都语义错误，不准继续优化。", {"rytov_variance":0.75,"target_ber":0.001,"max_ebn0_db":30.0,"injected_fault":"threshold_catalog_semantic_corruption_persistent"}, required_trace_statuses=["semantic_error"]),
        case(19, "semantic_persistent", "弱湍流0.2，BER千分之一，功率20 dB。阈值服务持续返回强弱顺序颠倒的数据。", {"rytov_variance":0.2,"target_ber":0.001,"max_ebn0_db":20.0,"injected_fault":"threshold_catalog_semantic_corruption_persistent"}, required_trace_statuses=["semantic_error"]),
        case(20, "semantic_persistent", "规划强湍流链路：方差2，目标BER=0.001，上限30.1 dB；语义污染重试后仍存在。", {"rytov_variance":2.0,"target_ber":0.001,"max_ebn0_db":30.1,"injected_fault":"threshold_catalog_semantic_corruption_persistent"}, required_trace_statuses=["semantic_error"]),
        case(21, "missing_indirect", "需要一套湍流感知链路，目标BER为0.001，功率预算25 dB，但我还没拿到湍流测量值。", {"target_ber":0.001,"max_ebn0_db":25.0}),
        case(22, "missing_indirect", "已知强湍流方差2，BER要到千分之一；功率上限尚未确定，请先说明缺什么。", {"rytov_variance":2.0,"target_ber":0.001}),
        case(23, "missing_indirect", "Rytov方差0.75、功率25 dB，业务方还没有给目标误码率。", {"rytov_variance":0.75,"max_ebn0_db":25.0}),
        case(24, "missing_indirect", "请做链路规划，但Rytov、目标BER和功率预算都待确认。", {}),
    ]
    payload = {
        "schema_version": "1.0",
        "dataset_version": "challenge-v1-frozen",
        "generator": "scripts/build_challenge_v1.py",
        "frozen_rule_parser_source_commit": "1b7b97d",
        "tasks": rows,
    }
    validate_dataset(payload, minimum_tasks=24)
    return payload


def main() -> None:
    payload = build()
    output = ROOT / "data" / "challenge_v1.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['tasks'])} challenge tasks to {output}")


if __name__ == "__main__":
    main()
