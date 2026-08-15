from scripts.probe_langgraph_model_compatibility import probe_passed


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
