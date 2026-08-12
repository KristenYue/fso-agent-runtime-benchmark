"""LangGraph execution skeleton; model planning is injected separately."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .baseline import execute_direct, matches_expected
from .contracts import TaskSpec
from .rule_parser import parse_request


class GraphState(TypedDict, total=False):
    case: dict[str, Any]
    parsed_task: TaskSpec
    result: dict[str, Any]
    passed: bool


def parse_node(state: GraphState) -> dict[str, Any]:
    return {"parsed_task": parse_request(state["case"])}


def execute_node(state: GraphState) -> dict[str, Any]:
    result = execute_direct(state["parsed_task"])
    return {
        "result": result.to_dict(),
        "passed": matches_expected(result, state["case"]["expected"]),
    }


def build_offline_graph():
    """Build a deterministic graph used only to validate graph/state plumbing."""
    builder = StateGraph(GraphState)
    builder.add_node("parse_request", parse_node)
    builder.add_node("execute_tools", execute_node)
    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "execute_tools")
    builder.add_edge("execute_tools", END)
    return builder.compile()


def run_offline_graph(cases: list[dict[str, Any]]) -> dict[str, Any]:
    graph = build_offline_graph()
    records = []
    for case in cases:
        state = graph.invoke({"case": case})
        records.append(
            {
                **state["result"],
                "passed": state["passed"],
                "parsed_operation": state["parsed_task"].operation,
                "parsed_inputs": state["parsed_task"].inputs,
            }
        )
    total = len(records)
    return {
        "summary": {
            "total": total,
            "passed": sum(record["passed"] for record in records),
            "pass_rate": sum(record["passed"] for record in records) / total if total else 0.0,
        },
        "results": records,
    }
