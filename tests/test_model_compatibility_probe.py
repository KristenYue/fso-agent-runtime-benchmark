from scripts.probe_langgraph_model_compatibility import execute_probe, probe_passed


class InvalidActionPlanner:
    def decide(self, **kwargs):
        del kwargs
        raise ValueError("planner action kind must be tool or finish")


def test_probe_requires_a_clarification_action() -> None:
    assert probe_passed(
        {"kind": "finish", "status": "needs_clarification", "message": "missing inputs"}
    )
    assert not probe_passed(
        {"kind": "finish", "status": "success", "message": "invented answer"}
    )
    assert not probe_passed(
        {"kind": "tool", "tool": "load_catalog", "arguments": {}}
    )


def test_probe_captures_local_validation_failure() -> None:
    action, error, passed = execute_probe(InvalidActionPlanner())
    assert action is None
    assert error == {
        "type": "ValueError",
        "message": "planner action kind must be tool or finish",
    }
    assert passed is False
