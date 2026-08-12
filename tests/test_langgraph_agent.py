from fso_benchmark.langgraph_agent import ScriptedPlanner, run_agent


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
