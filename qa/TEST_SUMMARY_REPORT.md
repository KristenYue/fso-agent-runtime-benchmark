# QA Test Summary Report

## Test object and run context

- Runtime: FSO Agent Runtime Benchmark v0.1.0
- Baseline commit before this additive QA package: `c701227`
- Python: local project `.venv` (Python 3.11)
- Operating system: Windows local development environment
- Test date: 2026-10-19
- Scope: additive QA evidence only; frozen Challenge/model/Prompt/results were
  neither edited nor rerun as part of this report.

## Result summary

| Test type | Designed | Automated | Passed | Failed | Blocked |
|---|---:|---:|---:|---:|---:|
| Smoke | 6 | 6 | 6 | 0 | 0 |
| Black-box | 12 | 12 | 12 | 0 | 0 |
| Boundary / negative | 10 | 10 | 10 | 0 | 0 |
| Gray-box | 8 | 8 | 8 | 0 | 0 |
| Recovery | 8 | 8 | 8 | 0 | 0 |
| Stability | 4 | 4 | 4 | 0 | 0 |
| **Total versioned test cases** | **48** | **48** | **48** | **0** | **0** |

The table counts versioned QA cases, not the number of individual pytest
functions. One parametrized test can provide evidence for multiple boundary
cases; existing tests are explicitly mapped rather than duplicated merely to
increase a count.

## Executed evidence

- `python -m pytest -q tests/qa`: **26 passed** after adding the duration/progress
  harness regression check.
- Full regression with a repository-local pytest temporary directory: **151
  passed**. The local default system temporary directory is sandbox-restricted,
  so the command used `--basetemp=.qa-pytest-tmp`; this changes only where test
  fixtures are written, not test selection or assertions.
- `python scripts/run_stability_test.py --runs 5000 --min-duration-seconds 1800
  --report-every 500`: **2,783,807 runs over 1,800.000642 seconds**,
  `passed=true`, zero unexpected outcomes, zero inconsistent results and zero
  missing traces. See `qa/STABILITY_TEST_REPORT.md`.
- Existing recovery preflight tests are mapped in the traceability matrix and
  passed in the full regression suite.

## Defects and corrective evidence

1. `qa/defects/BUG-001-non-ascii-credential.md`: request construction failed
   before provider invocation; corrected with credential preflight.
2. `qa/defects/BUG-002-wrong-error-classification.md`: a request-preparation
   error was previously labeled as a planner action error; the recovery protocol
   separates the layers.

## Known limitations

- No long-running real LLM/network call is exercised here.
- No GUI, distributed Worker, production load or high-concurrency behaviour is
  asserted.
- The stability latency is local deterministic scheduling only, not end-to-end
  Agent response time or an SLA.
- The frozen 24-task Challenge remains the existing evaluation artifact; this
  package adds QA evidence rather than claiming an expanded benchmark.

## Release conclusion

**PASS WITH KNOWN LIMITATIONS.** The additive QA checks and the offline 5,000-run
soak meet their stated scope. Production claims remain out of scope.
