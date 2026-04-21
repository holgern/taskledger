from __future__ import annotations

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
