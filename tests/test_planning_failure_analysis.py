from fso_benchmark.planning_metrics import classify_failure, score_planning_report


def case(task_id: str, fault: str | None, expected: dict) -> dict:
    inputs = {
        "rytov_variance": 0.75,
        "target_ber": 0.001,
        "max_ebn0_db": 30.0,
    }
    if fault is not None:
        inputs["injected_fault"] = fault
    return {
        "task_id": task_id,
        "split": "dev",
        "level": "L3",
        "inputs": inputs,
        "expected": expected,
    }


def test_scores_semantic_recovery_and_deterministic_failure_categories() -> None:
    cases = [
        case(
            "recovered",
            "threshold_catalog_semantic_corruption_once",
            {
                "status": "success",
                "configuration_id": "LDPC-L64-D128",
                "required_trace_statuses": ["semantic_error"],
                "requires_recovery": True,
            },
        ),
        case(
            "persistent",
            "threshold_catalog_semantic_corruption_persistent",
            {"status": "tool_error", "required_trace_statuses": ["semantic_error"]},
        ),
        case(
            "invalid-action",
            None,
            {"status": "success", "configuration_id": "LDPC-L64-D128"},
        ),
    ]
    report = {
        "results": [
            {
                "task_id": "recovered",
                "status": "success",
                "answer": {
                    "selection": {
                        "configuration_id": "LDPC-L64-D128",
                        "required_ebn0_db": 24.0,
                        "buffer_kib": 128,
                        "code": "LDPC",
                        "target_ber": 0.001,
                        "optimality_gap": 0.0,
                    }
                },
                "error": None,
                "passed": True,
                "trace": [
                    {"tool": "load_turbulence_catalog", "status": "success"},
                    {"tool": "validate_turbulence_catalog", "status": "semantic_error"},
                    {
                        "tool": "load_turbulence_catalog",
                        "status": "success",
                        "recovery": "clean_frozen_catalog",
                    },
                ],
            },
            {
                "task_id": "persistent",
                "status": "tool_error",
                "answer": None,
                "error": "catalog remained invalid",
                "passed": True,
                "trace": [
                    {"tool": "load_turbulence_catalog", "status": "success"},
                    {"tool": "validate_turbulence_catalog", "status": "semantic_error"},
                    {"tool": "load_turbulence_catalog", "status": "success"},
                    {"tool": "validate_turbulence_catalog", "status": "semantic_error"},
                ],
            },
            {
                "task_id": "invalid-action",
                "status": "tool_error",
                "answer": None,
                "error": "invalid planner action: unexpected field",
                "passed": False,
                "trace": [],
            },
        ]
    }

    scored = score_planning_report(cases, report)
    metrics = scored["planning_metrics"]
    assert metrics["semantic_recovery_rate"] == 1.0
    assert metrics["persistent_fault_stop_accuracy"] == 1.0
    assert metrics["duplicate_successful_steps"] == 0
    assert scored["failure_analysis"] == {
        "failed_tasks": 1,
        "category_counts": {"invalid_planner_action": 1, "passed": 2},
    }


def test_provider_failure_has_a_separate_category() -> None:
    example = case(
        "provider-failure",
        None,
        {"status": "success", "configuration_id": "LDPC-L64-D128"},
    )
    record = {
        "status": "tool_error",
        "error": "planner request failed: provider request failed with status 503",
        "passed": False,
        "trace": [],
    }
    assert classify_failure(example, record) == "provider_error"


def test_scores_persistent_catalog_unavailability_as_a_correct_stop() -> None:
    unavailable = case(
        "unavailable",
        "threshold_catalog_unavailable",
        {"status": "tool_error"},
    )
    report = {
        "results": [
            {
                "task_id": "unavailable",
                "status": "tool_error",
                "answer": None,
                "error": "catalog unavailable after retry",
                "passed": True,
                "trace": [
                    {"tool": "load_turbulence_catalog", "status": "error"},
                    {"tool": "load_turbulence_catalog", "status": "error"},
                ],
            }
        ]
    }

    metrics = score_planning_report([unavailable], report)["planning_metrics"]
    assert metrics["persistent_fault_cases"] == 1
    assert metrics["correct_persistent_stops"] == 1
    assert metrics["persistent_fault_stop_accuracy"] == 1.0
