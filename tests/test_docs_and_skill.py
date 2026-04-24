from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skill_examples_exist() -> None:
    examples_dir = ROOT / "skills" / "taskledger" / "examples"
    for name in ("planning-flow.md", "implementation-flow.md", "validation-flow.md"):
        path = examples_dir / name
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()


def test_api_docs_mentions_all_task_first_command_groups() -> None:
    api_text = (ROOT / "API.md").read_text(encoding="utf-8")
    for name in (
        "task",
        "plan",
        "question",
        "implement",
        "validate",
        "todo",
        "intro",
        "file",
        "require",
        "lock",
        "handoff",
        "doctor",
    ):
        assert f"`{name}`" in api_text


def test_readme_mentions_root_alias_and_json_envelope() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "--root" in readme
    assert '"ok": true' in readme
    assert '"command": "status"' in readme
