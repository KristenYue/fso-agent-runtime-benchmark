# Requirements Traceability Matrix

The requirements below are testable software requirements inferred from the
frozen Runtime contract. They do not expand the original evaluation scope.

| ID | Software requirement | Acceptance condition | Test cases | Automated evidence |
|---|---|---|---|---|
| REQ-01 | Runtime parses valid structured actions. | Valid actions enter the matching execution branch. | SMK-02, BB-01, BB-02 | `tests/qa/test_smoke.py`, `test_black_box.py` |
| REQ-02 | Missing required information requests clarification. | No tool call; terminal state is `needs_clarification`. | BB-03, BB-04, GRAY-01 | `test_missing_parameter_requests_clarification` |
| REQ-03 | Only allow-listed tools can run. | Unauthorised tool execution count is zero. | NEG-02, NEG-03, GRAY-02 | `test_unknown_tool_is_rejected`, `test_rejected_tool_is_never_executed` |
| REQ-04 | Tool calls stay within the budget. | A ninth planned call after an 8-call budget stops explicitly. | BB-10, NEG-10, GRAY-06 | `test_budget_exhaustion_stops_safely` |
| REQ-05 | Tool parameters obey the schema and domain contract. | Wrong shape/field/type is rejected before or at the deterministic tool boundary with structured evidence. | NEG-01 through NEG-09 | `test_invalid_actions_are_rejected` parametrization |
| REQ-06 | One semantic contamination can recover. | Recovery context is visible and the clean retry can complete. | GRAY-03, REC-03, STAB-02 | `test_semantic_contamination_recovers_once` |
| REQ-07 | Persistent contamination fails closed. | No `success` terminal result is emitted. | GRAY-04, REC-07, STAB-02 | `test_persistent_semantic_contamination_fails_closed` |
| REQ-08 | Every executed tool step preserves a structured trace. | Each observation has tool, arguments, status and output or error. | SMK-06, GRAY-05, STAB-04 | `test_trace_contains_required_fields` |
| REQ-09 | Deterministic inputs have deterministic results. | Repeated runs preserve terminal state and scenario-specific tool trajectory. | BB-12, GRAY-07, STAB-01, STAB-03 | `test_repeated_deterministic_input_has_same_terminal_state`, `test_four_deterministic_scenarios_remain_stable_for_50_cycles` |
| REQ-10 | Invalid credentials fail before network use. | Provider attempts are zero and the failure is classified as credential/request preparation, not planner action. | REC-06, BUG-001, BUG-002 | `tests/test_recovery_contract.py::test_credential_preflight_rejects_unsafe_input` |

## Terminology correction retained by QA

`tool_error` is the public terminal state for a safe Runtime stop. A schema-invalid
planner action has an `invalid planner action` error message; a schema-valid action
whose numeric value violates a tool domain creates one structured tool error
observation. The distinction is intentional and is covered by the negative suite.
