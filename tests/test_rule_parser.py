from scripts.generate_tasks_v1 import generate

from fso_benchmark.rule_baseline import run_rule_baseline
from fso_benchmark.rule_parser import parse_request


def test_rule_parser_does_not_read_hidden_inputs() -> None:
    case = {
        "task_id": "isolation",
        "level": "L1",
        "request": "请计算Eb/N0为 10 dB时的OOK理论BER。",
        "operation": "delete_everything",
        "inputs": {"secret": 1},
    }
    parsed = parse_request(case)
    assert parsed.operation == "calculate_ook_ber"
    assert parsed.inputs == {"ebn0_db": 10.0}


def test_rule_baseline_reports_parse_and_task_metrics_separately() -> None:
    report = run_rule_baseline(generate()["tasks"])
    assert report["summary"]["total"] == 120
    assert 0.0 <= report["summary"]["parse_exact_rate"] <= 1.0
    assert 0.0 <= report["summary"]["task_pass_rate"] <= 1.0
    assert set(report["by_split_level"]) == {
        "dev/L1", "dev/L2", "dev/L3",
        "test/L1", "test/L2", "test/L3",
        "train/L1", "train/L2", "train/L3",
    }

