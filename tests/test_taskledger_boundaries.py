from __future__ import annotations

import importlib.util
import re
from pathlib import Path


def test_taskledger_has_no_direct_runtildone_imports() -> None:
    taskledger_root = Path(__file__).resolve().parents[1] / "taskledger"
    import_pattern = re.compile(r"^\s*(from|import)\s+runtildone(\.|$)", re.MULTILINE)

    offenders = [
        path.relative_to(taskledger_root).as_posix()
        for path in taskledger_root.rglob("*.py")
        if import_pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_taskledger_has_no_runtime_specific_strings() -> None:
    taskledger_root = Path(__file__).resolve().parents[1] / "taskledger"
    forbidden_patterns = (
        "runtildone plan",
        "runtildone implement",
        "runtildone validate",
        "runtildone project",
        ".runtildone/",
        "loop/latest",
    )
    offenders: list[str] = []
    for path in taskledger_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(pattern in text for pattern in forbidden_patterns):
            offenders.append(path.relative_to(taskledger_root).as_posix())
    assert offenders == []


def test_docs_conf_is_independent_from_runtildone() -> None:
    docs_conf = Path(__file__).resolve().parents[1] / "docs" / "conf.py"
    text = docs_conf.read_text(encoding="utf-8")

    assert "runtildone" not in text

    spec = importlib.util.spec_from_file_location("taskledger_docs_conf", docs_conf)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.project == "taskledger"
    assert isinstance(module.release, str)
    assert module.release
