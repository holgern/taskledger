from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests create many short-lived Markdown/YAML records under tmp_path.
# Production durability still fsyncs; pytest opts into faster temporary IO.
os.environ.setdefault("TASKLEDGER_TEST_FAST_IO", "1")

import shutil

import pytest

from tests.support.builders import (
    create_approved_task,
    create_done_task,
    create_failed_validation_task,
    create_implemented_task,
    init_workspace,
)


def _copy_template(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


@pytest.fixture(scope="session")
def empty_workspace_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("taskledger-empty-template")
    init_workspace(root)
    return root


@pytest.fixture
def empty_workspace(tmp_path: Path, empty_workspace_template: Path) -> Path:
    return _copy_template(empty_workspace_template, tmp_path / "workspace")


@pytest.fixture(scope="session")
def approved_workspace_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("taskledger-approved-template")
    init_workspace(root)
    create_approved_task(root, title="Approved task", slug="approved-task")
    return root


@pytest.fixture
def approved_workspace(tmp_path: Path, approved_workspace_template: Path) -> Path:
    return _copy_template(approved_workspace_template, tmp_path / "workspace")


@pytest.fixture(scope="session")
def implemented_workspace_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("taskledger-implemented-template")
    init_workspace(root)
    create_implemented_task(root, title="Implemented task", slug="implemented-task")
    return root


@pytest.fixture
def implemented_workspace(tmp_path: Path, implemented_workspace_template: Path) -> Path:
    return _copy_template(implemented_workspace_template, tmp_path / "workspace")


@pytest.fixture(scope="session")
def done_workspace_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("taskledger-done-template")
    init_workspace(root)
    create_done_task(root, title="Done task", slug="done-task")
    return root


@pytest.fixture
def done_workspace(tmp_path: Path, done_workspace_template: Path) -> Path:
    return _copy_template(done_workspace_template, tmp_path / "workspace")


@pytest.fixture(scope="session")
def failed_validation_workspace_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    root = tmp_path_factory.mktemp("taskledger-failed-validation-template")
    init_workspace(root)
    create_failed_validation_task(
        root, title="Failed validation task", slug="failed-validation-task"
    )
    return root


@pytest.fixture
def failed_validation_workspace(
    tmp_path: Path, failed_validation_workspace_template: Path
) -> Path:
    return _copy_template(
        failed_validation_workspace_template, tmp_path / "workspace"
    )
