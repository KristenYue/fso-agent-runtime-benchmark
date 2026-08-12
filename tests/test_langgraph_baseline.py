import json
from pathlib import Path

import pytest


pytest.importorskip("langgraph")

from fso_benchmark.langgraph_baseline import build_offline_graph, run_offline_graph


ROOT = Path(__file__).resolve().parents[1]


def development_planning_cases():
    payload = json.loads((ROOT / "data" / "tasks_v2.json").read_text(encoding="utf-8"))
    return [
        case for case in payload["tasks"]
        if case["operation"] == "plan_turbulence_aware_link"
    ]


def test_langgraph_compiles_and_runs_one_development_case() -> None:
    graph = build_offline_graph()
    state = graph.invoke({"case": development_planning_cases()[0]})
    assert state["result"]["status"] == "success"
    assert state["passed"] is True


def test_offline_graph_matches_rule_workflow_on_development_data() -> None:
    report = run_offline_graph(development_planning_cases())
    assert report["summary"] == {"total": 30, "passed": 30, "pass_rate": 1.0}
