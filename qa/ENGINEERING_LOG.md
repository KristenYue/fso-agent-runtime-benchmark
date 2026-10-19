# QA Evidence Engineering Log

## 2026-10-19 — Additive QA evidence package

**Scope decision.** The repository already contained 125 tests, 24 frozen
Challenge tasks, fault injection and a preserved credential incident. This work
adds recruiter-readable requirement/test/defect/stability evidence; it does not
rewrite the Runtime or manipulate frozen results.

**Issue 1 — initial QA assumptions did not match the existing contract.** The
first new boundary test expected every invalid numeric input to fail before a
trace was created. Actual behaviour is more precise: action-schema-invalid input
is rejected before execution, while schema-valid values outside a deterministic
tool's numeric domain create one structured `error` observation. The test was
changed to assert that distinction rather than changing product code.

**Issue 2 — fail-closed retains an explanation.** The first gray-box test
expected `answer=None` for persistent semantic contamination. The Runtime's
existing contract returns terminal `tool_error` with a clear message, which is
not a fabricated success. The QA expectation now checks explicit non-success and
the error message.

**Issue 3 — recovery and normal success have different valid traces.** A
stability-smoke signature keyed only by terminal status incorrectly compared
normal success with recovered success. Signatures are now keyed by scenario and
expected state, preserving deterministic checks without collapsing different
valid workflows.

**Issue 4 — first soak script polluted its own memory observation.** Retaining
all Python float duration objects produced avoidable test-harness allocation.
The script now uses a bounded 512-sample latency buffer, performs collection at
checkpoints, labels latency as sampled, and records raw memory checkpoints.

**Verification.** QA tests passed 25/25; the separate 5,000-run offline soak
reported zero unexpected outcomes, inconsistent results and missing traces.

**Issue 5 — sandbox system temp directory is not writable.** A first full
`pytest` run reported 14 setup errors because pytest could not create numbered
directories below the sandbox-controlled system Temp location; no test assertion
failed. Rerunning unchanged tests with `--basetemp=.qa-pytest-tmp` placed only
ephemeral fixtures under the repository and produced **150 passed**. The
temporary directory was removed after verification and is not part of delivery.

**Issue 6 — 5,000 iterations alone did not satisfy the stated soak duration.**
The first stability report reached 5,000 runs in seconds, whereas the plan says
to use the later of 5,000 runs and 30 minutes. The harness now supports
`--min-duration-seconds` and continues until both thresholds are met. Progress
is written every 500 runs to JSONL instead of retained in memory. An initial
relative-path self-check exposed a final-report path normalization bug; output is
now resolved against the repository root and covered by
`test_stability_script_honours_duration_and_writes_progress`.

**Strict soak verification.** The final offline run requested at least 5,000
iterations and 1,800 seconds, and completed 2,783,807 iterations in
1,800.000642 seconds. It recorded 5,567 JSONL checkpoints; unexpected outcomes,
inconsistent results and missing traces were all zero. The report deliberately
states that P50/P95 are sampled local scheduler timings, not model/network or
production-SLA performance.

**Issue 7 — final verification command quoting.** A combined PowerShell command
used an escaped Python f-string inside `-c`; PowerShell rejected that fragment as
an invalid ScriptBlock after the full regression and benchmark had already run.
The QA artifact validation was rerun as a separate single-quoted Python command:
48 cases, 2,783,807 soak runs and 5,567 checkpoint lines all matched. A harmless
subsequent cleanup attempted to remove a pytest base directory that collection
had not created; the directory was absent, so no project file was removed.

**Issue 8 — CI test uses an external absolute output path.** The duration-harness
unit test writes to pytest's external temporary directory on GitHub Actions. The
first path normalization fix assumed all outputs were under the repository and
therefore failed only in Linux CI. The report now emits a repository-relative
progress reference when possible and an absolute reference otherwise. The same
existing unit test covers both the CI path case and report generation.
