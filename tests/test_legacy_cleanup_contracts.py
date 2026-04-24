from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEGACY_MODULE_PATHS = {
    "taskledger/api/composition.py",
    "taskledger/api/contexts.py",
    "taskledger/api/execution_requests.py",
    "taskledger/api/items.py",
    "taskledger/api/memories.py",
    "taskledger/api/repos.py",
    "taskledger/api/runs.py",
    "taskledger/api/runtime_support.py",
    "taskledger/api/types.py",
    "taskledger/api/validation.py",
    "taskledger/api/workflows.py",
    "taskledger/cli_compose.py",
    "taskledger/cli_context.py",
    "taskledger/cli_execution_requests.py",
    "taskledger/cli_item.py",
    "taskledger/cli_memory.py",
    "taskledger/cli_repo.py",
    "taskledger/cli_runs.py",
    "taskledger/cli_runtime_support.py",
    "taskledger/cli_validation.py",
    "taskledger/cli_workflow.py",
    "taskledger/compose.py",
    "taskledger/context.py",
    "taskledger/doctor.py",
    "taskledger/links.py",
    "taskledger/workflow.py",
}


def test_legacy_modules_are_removed() -> None:
    for relative_path in LEGACY_MODULE_PATHS:
        assert not (ROOT / relative_path).exists(), relative_path


def test_package_initializers_do_not_use_star_imports() -> None:
    for relative_path in (
        "taskledger/__init__.py",
        "taskledger/api/__init__.py",
        "taskledger/models/__init__.py",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "import *" not in text


def test_v2_storage_does_not_import_storage_facade() -> None:
    text = (ROOT / "taskledger/storage/v2.py").read_text(encoding="utf-8")
    assert "from taskledger.storage import" not in text
