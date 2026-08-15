from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.model_contract import bind_model_identity  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bind the frozen LangGraph contract to a non-secret model identity."
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument(
        "--response-format-type",
        required=True,
        choices=("json_schema", "json_object"),
    )
    parser.add_argument(
        "--thinking-mode", required=True, choices=("enabled", "disabled")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    development = ROOT / "artifacts" / "langgraph_model_development" / "manifest.json"
    if development.exists():
        raise SystemExit("cannot bind or rebind after a development run exists")
    path = ROOT / "artifacts" / "langgraph_model_contract_v1" / "contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    try:
        updated = bind_model_identity(
            contract,
            provider=args.provider,
            base_url=args.base_url,
            snapshot_id=args.snapshot_id,
            response_format_type=args.response_format_type,
            enable_thinking=args.thinking_mode == "enabled",
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if updated is contract:
        print("model contract is already bound to this identity")
        return
    updated["model_binding"] = {
        "bound_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "credentials_recorded": False,
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    print(json.dumps(updated["model"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
