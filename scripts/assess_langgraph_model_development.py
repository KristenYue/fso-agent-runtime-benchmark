from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fso_benchmark.development_gate import assess_development_artifacts  # noqa: E402


if __name__ == "__main__":
    print(
        json.dumps(
            assess_development_artifacts(ROOT), ensure_ascii=False, indent=2
        )
    )
