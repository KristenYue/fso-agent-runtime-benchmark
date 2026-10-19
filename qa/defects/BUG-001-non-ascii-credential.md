# BUG-001 Non-ASCII credential causes pre-request failure

## Summary

The original Custom Runtime Challenge v1 produced 0 valid observations because a
credential containing non-ASCII characters failed while constructing the local
HTTP `Authorization` header. This was an input-validation defect in evaluation
infrastructure, not a model or Runtime capability result.

## Environment

- Scope: Custom Runtime Challenge v1, 2026-09-07
- Runtime: Python HTTP client before network transport
- Evidence: `docs/CUSTOM_RUNTIME_CHALLENGE_INCIDENT.md` and
  `artifacts/custom_runtime_challenge/`

## Severity and priority

Severity: High for experiment validity. Priority: P0, because a consumed
one-shot ledger must not be silently rerun after a preflight failure.

## Preconditions

A non-empty API key containing non-ASCII characters is configured. The original
preflight checked only non-emptiness.

## Steps to reproduce

1. Provide a non-ASCII value such as `中文密钥` to the credential preflight.
2. Attempt request preparation with a `Bearer` authorization header.
3. Observe the encoding failure before the network transport boundary.

## Expected result

The credential must be rejected before a ledger is created or provider request
is attempted; the error must identify unsafe credential input.

## Actual result

All 24 Challenge v1 entries failed locally. Provider attempts, model calls,
tokens and tool traces were all zero. The original result and ledger are retained
as immutable incident evidence; they are not interpreted as a 0/24 Agent score.

## Root cause

Header encoding requires ASCII-compatible credential text. A generic non-empty
check allowed unsafe text through to request preparation.

## Fix

`validate_api_key` now rejects empty, whitespace-bearing and non-ASCII input
before any provider attempt. A separate recovery protocol requires preflight to
stop and request user input on any failure.

## Regression tests

- `tests/test_recovery_contract.py::test_credential_preflight_rejects_unsafe_input`
- `tests/test_recovery_contract.py::test_credential_preflight_accepts_ascii_without_whitespace`

## Final status

Closed for the v1.1 recovery protocol. Challenge v1 remains consumed and
unchanged; this fix does not rewrite its historical result.
