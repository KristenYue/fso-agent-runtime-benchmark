from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    configured = {
        "FSO_MODEL_BASE_URL": bool(os.environ.get("FSO_MODEL_BASE_URL")),
        "FSO_MODEL_API_KEY": bool(os.environ.get("FSO_MODEL_API_KEY")),
        "FSO_MODEL_ID": bool(os.environ.get("FSO_MODEL_ID")),
    }
    result = {
        "ready": all(configured.values()),
        "credentials": configured,
        "secrets_read_or_written": False,
        "challenge_executed": False,
    }
    output = ROOT / "artifacts" / "langgraph_model_contract_v1" / "readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
