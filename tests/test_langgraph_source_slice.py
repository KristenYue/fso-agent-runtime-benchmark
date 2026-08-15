import hashlib
import importlib.metadata
import json
from pathlib import Path

import langgraph.graph


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_slice_manifest_matches_locked_installation() -> None:
    manifest = json.loads(
        (
            ROOT
            / "artifacts"
            / "langgraph_source_slice_v1"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    for package, version in manifest["packages"].items():
        assert importlib.metadata.version(package) == version
    assert sha256(ROOT / "requirements-agents.lock") == manifest[
        "requirements_lock_sha256"
    ]

    package_root = Path(langgraph.graph.__file__).resolve().parent.parent
    for relative_path, expected_hash in manifest["source_files"].items():
        assert sha256(package_root / Path(relative_path)) == expected_hash


def test_source_slice_note_covers_required_design_questions() -> None:
    note = (ROOT / "docs" / "LANGGRAPH_SOURCE_SLICE_1_2_11.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "StateGraph",
        "CompiledStateGraph",
        "SyncPregelLoop",
        "PregelRunner",
        "put_writes",
        "后续 Runtime 借鉴什么",
        "不直接照搬什么",
    ):
        assert required in note
