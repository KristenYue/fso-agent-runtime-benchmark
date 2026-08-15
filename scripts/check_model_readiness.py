from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.model_contract import require_bound_model_contract  # noqa: E402


def main() -> None:
    configured = {
        "FSO_MODEL_PROVIDER": bool(os.environ.get("FSO_MODEL_PROVIDER")),
        "FSO_MODEL_BASE_URL": bool(os.environ.get("FSO_MODEL_BASE_URL")),
        "FSO_MODEL_API_KEY": bool(os.environ.get("FSO_MODEL_API_KEY")),
        "FSO_MODEL_ID": bool(os.environ.get("FSO_MODEL_ID")),
    }
    contract_bound = False
    contract_error = None
    if all(
        configured[name]
        for name in ("FSO_MODEL_PROVIDER", "FSO_MODEL_BASE_URL", "FSO_MODEL_ID")
    ):
        try:
            require_bound_model_contract(
                ROOT,
                provider=os.environ["FSO_MODEL_PROVIDER"],
                base_url=os.environ["FSO_MODEL_BASE_URL"],
                snapshot_id=os.environ["FSO_MODEL_ID"],
            )
            contract_bound = True
        except (ValueError, json.JSONDecodeError) as exc:
            contract_error = str(exc)
    result = {
        "ready": all(configured.values()) and contract_bound,
        "credentials": configured,
        "model_contract_bound": contract_bound,
        "model_contract_error": contract_error,
        "api_key_presence_checked": True,
        "secret_values_recorded": False,
        "challenge_executed": False,
    }
    output = ROOT / "artifacts" / "langgraph_model_contract_v1" / "readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
