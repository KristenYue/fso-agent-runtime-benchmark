import pytest

from fso_benchmark.langgraph_agent import (
    PlannerRequestError,
    ScriptedPlanner,
    run_agent,
    validate_planner_action,
)


class FailingRequestPlanner:
    def decide(self, **kwargs):
        del kwargs
        raise PlannerRequestError("provider request failed with status 503")


def successful_actions():
    return [
        {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":0.75}},
        {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
        {"kind":"tool","tool":"load_catalog","arguments":{}},
        {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Moderate","target_ber":0.001,"max_ebn0_db":25.0}},
        {"kind":"finish","status":"success","message":""},
    ]


def test_provider_failure_is_not_mislabeled_as_invalid_action() -> None:
    result = run_agent("development request", FailingRequestPlanner())
    assert result["status"] == "tool_error"
    assert result["error"] == (
        "planner request failed: provider request failed with status 503"
    )
    assert "invalid planner action" not in result["error"]


def test_scripted_planner_runs_real_tool_loop() -> None:
    result = run_agent("development request", ScriptedPlanner(successful_actions()))
    assert result["status"] == "success"
    assert result["answer"]["selection"]["configuration_id"] == "LDPC-L64-D128"
    assert [step["tool"] for step in result["trace"]] == [
        "characterize_turbulence",
        "resolve_turbulence_regime",
        "load_turbulence_catalog",
        "validate_turbulence_catalog",
        "load_catalog",
        "select_robust_configuration",
    ]
    assert result["trace"][2]["output"] == {
        "catalog": "turbulence_thresholds",
        "rows": 12,
        "target_ber_values": [0.001],
    }
    assert result["trace"][4]["output"]["rows"] == 16
    assert "LDPC-L64-D128" not in str(result["trace"][4]["output"])


def test_unlisted_tool_is_blocked_before_execution() -> None:
    planner = ScriptedPlanner(
        [{"kind":"tool","tool":"read_private_file","arguments":{"path":"secret"}}]
    )
    result = run_agent("unsafe request", planner)
    assert result["status"] == "tool_error"
    assert "not allowed" in result["error"]
    assert result["trace"] == []


def test_success_cannot_be_claimed_without_optimizer_output() -> None:
    planner = ScriptedPlanner([{"kind":"finish","status":"success","message":"done"}])
    result = run_agent("guess an answer", planner)
    assert result["status"] == "tool_error"
    assert "before optimizer output" in result["error"]


def test_tool_budget_stops_repeated_actions() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
            {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
            {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":0.75}},
        ]
    )
    result = run_agent("loop", planner, max_tool_calls=2)
    assert result["status"] == "tool_error"
    assert result["error"] == "tool-call budget exhausted"
    assert len(result["trace"]) == 2


def test_optimizer_requires_validated_catalogs() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Moderate","target_ber":0.001,"max_ebn0_db":25.0}},
            {"kind":"finish","status":"tool_error","message":"cannot continue"},
        ]
    )
    result = run_agent("skip prerequisites", planner)
    assert result["status"] == "tool_error"
    assert result["trace"][0]["status"] == "error"


def test_planner_can_request_clarification_without_tool_call() -> None:
    planner = ScriptedPlanner(
        [{"kind":"finish","status":"needs_clarification","message":"请提供功率上限"}]
    )
    result = run_agent("missing power", planner)
    assert result["status"] == "needs_clarification"
    assert result["answer"]["message"] == "请提供功率上限"
    assert result["trace"] == []


@pytest.mark.parametrize(
    "action",
    [
        {"kind":"tool","tool":"load_catalog","arguments":{},"reasoning":"hidden"},
        {"kind":"finish","status":"success","message":"","answer":42},
    ],
)
def test_local_action_validation_rejects_extra_fields(action) -> None:
    with pytest.raises(ValueError, match="fields must be exactly"):
        validate_planner_action(action)


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (
            {"kind":"tool","tool":"load_catalog","arguments":{"catalog":"configuration"}},
            "unexpected arguments: catalog",
        ),
        (
            {
                "kind":"tool",
                "tool":"select_robust_configuration",
                "arguments":{"rytov_variance":0.75,"target_ber":0.001,"max_eb_n0_db":25.0},
            },
            "missing required arguments: max_ebn0_db, turbulence",
        ),
    ],
)
def test_local_action_validation_enforces_exact_tool_argument_names(
    action, message
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_planner_action(action)


def test_fault_profile_is_hidden_but_timeout_reaches_tool_trace() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"finish","status":"tool_error","message":"test stop"},
        ]
    )
    result = run_agent(
        "catalog may time out",
        planner,
        fault_profile="threshold_catalog_timeout_once",
    )
    assert [step["status"] for step in result["trace"]] == ["error", "success"]
    assert "fault_profile" not in str(result["trace"])


def test_semantic_corruption_requires_validation_and_can_recover() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"finish","status":"tool_error","message":"test stop"},
        ]
    )
    result = run_agent(
        "catalog may be corrupted",
        planner,
        fault_profile="threshold_catalog_semantic_corruption_once",
    )
    assert [step["status"] for step in result["trace"]] == [
        "success",
        "semantic_error",
        "success",
        "success",
    ]


def test_persistent_semantic_corruption_remains_detectable() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"finish","status":"tool_error","message":"persistent corruption"},
        ]
    )
    result = run_agent(
        "catalog remains corrupted",
        planner,
        fault_profile="threshold_catalog_semantic_corruption_persistent",
    )
    assert sum(step["status"] == "semantic_error" for step in result["trace"]) == 2


def test_finish_is_allowed_after_exact_tool_budget() -> None:
    actions = successful_actions()
    planner = ScriptedPlanner(actions)
    result = run_agent("exact budget", planner, max_tool_calls=6)
    assert result["status"] == "success"
    assert len(result["trace"]) == 6


def test_semantic_recovery_trace_has_explicit_recovery_marker() -> None:
    planner = ScriptedPlanner(
        [
            {"kind":"tool","tool":"characterize_turbulence","arguments":{"rytov_variance":2.0}},
            {"kind":"tool","tool":"resolve_turbulence_regime","arguments":{"rytov_variance":2.0}},
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"load_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"validate_turbulence_catalog","arguments":{}},
            {"kind":"tool","tool":"load_catalog","arguments":{}},
            {"kind":"tool","tool":"select_robust_configuration","arguments":{"turbulence":"Strong","target_ber":0.001,"max_ebn0_db":30.0}},
            {"kind":"finish","status":"success","message":""},
        ]
    )
    result = run_agent(
        "semantic recovery",
        planner,
        max_tool_calls=8,
        fault_profile="threshold_catalog_semantic_corruption_once",
    )
    assert result["status"] == "success"
    assert any(step.get("recovery") == "clean_frozen_catalog" for step in result["trace"])
    assert any(step["status"] == "semantic_error" for step in result["trace"])
