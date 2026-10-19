# Runtime QA Test Plan

## Objective and boundary

This QA package makes the existing deterministic FSO Runtime evidence legible as
software-quality work. It does **not** replace the preregistered Challenge,
change frozen tasks, Prompt, model, tools, budget, score, or historical result.
All new execution is offline and deterministic unless a document explicitly says
otherwise.

## Test object

- Custom Runtime: `src/fso_benchmark/agent_runtime.py`
- Comparison Runtime: `src/fso_benchmark/langgraph_agent.py`
- Action/tool contract: `src/fso_benchmark/planner_contract.py`
- Deterministic tool boundary: `src/fso_benchmark/tool_environment.py`
- Fault injection: `src/fso_benchmark/faults.py`

## Strategy

| Layer | Purpose | Execution |
|---|---|---|
| Smoke | Imports, startup, registered tools, one complete trace | every CI run |
| Black-box | Input/output behaviour and safe terminal states | every CI run |
| Boundary/negative | Invalid actions, schema and domain limits | every CI run |
| Gray-box | Trace, execution count, recovery and trajectory evidence | every CI run |
| Recovery | Timeout, semantic corruption and credential preflight mapping | every CI run |
| Stability | Repeatable offline scheduling under four deterministic scenarios | manual/scheduled CI |

## Entry and exit criteria

Entry: Python 3.11+, editable project install, no API key required. Exit: all
mapped automated checks pass; the stability report has zero unexpected outcomes,
zero inconsistent results, and zero missing traces. A release is reported as
**PASS WITH KNOWN LIMITATIONS**, never as a production SLA claim.

## Commands

```powershell
python -m pytest -q tests/qa
python scripts/run_stability_test.py --runs 5000 --report-every 500
```

The latter measures only offline deterministic Runtime scheduling. It excludes
LLM/network latency, GUI, distributed workers and production traffic.
