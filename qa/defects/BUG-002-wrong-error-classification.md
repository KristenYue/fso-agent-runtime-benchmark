# BUG-002 Request-preparation error classified as planner error

## Summary

The non-ASCII credential failure in BUG-001 inherited from `ValueError` and was
therefore caught by the generic planner-action validation path. It was reported
as `invalid_planner_action`, even though no planner response or tool execution
had occurred.

## Why classification matters

Misclassification tells an investigator to inspect model JSON or action schema
when the failing component is authentication/request preparation. It also
obscures the decisive evidence: provider attempts and trace entries are zero.

## Environment and reproduction

Use the original v1 condition from BUG-001: a non-ASCII credential reaches HTTP
header construction before preflight validation. The local encoding exception
occurs before network transport and was routed through the generic `ValueError`
handler.

## Expected result

Credential, authentication and transport-preparation errors must be represented
as request/preflight failures, distinct from an invalid planner action. Planner
action validation is only meaningful after the planner has returned an action.

## Actual result

The incident was labeled `invalid_planner_action`, although provider attempts
were 0 and the trace was empty. The original report remains preserved to avoid
rewriting historical evidence.

## Root cause

Exception inheritance alone was used as the classification signal. It did not
preserve the execution layer that raised the exception.

## Fix

The recovery path adds credential preflight before ledger creation and request
construction. The Runtime keeps `PlannerRequestError` separate from invalid
planner action validation; QA traceability explicitly maps preflight errors to
REQ-10 rather than REQ-05.

## Regression evidence

- `tests/test_recovery_contract.py::test_credential_preflight_rejects_unsafe_input`
- `tests/test_agent_runtime.py` exercises the separate `PlannerRequestError`
  branch and schema-validation branch.
- `qa/REQUIREMENTS_TRACEABILITY.md` distinguishes REQ-05 and REQ-10.

## Final status

Closed in the recovery protocol. The correction is scoped to classification and
preflight; it does not alter frozen Challenge v1 results.
