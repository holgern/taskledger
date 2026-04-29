from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from importlib import import_module
from typing import cast


def main() -> None:
    try:
        cli_module = import_module("taskledger.cli")
        cli_main = cli_module.cli_main
        if not callable(cli_main):
            raise TypeError("taskledger.cli.cli_main is not callable.")
    except Exception as exc:
        sys.stderr.write("taskledger failed to import its CLI.\n")
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        sys.stderr.write(
            "Run: python -m py_compile taskledger/cli.py taskledger/cli_release.py\n"
        )
        if "--debug" in sys.argv:
            traceback.print_exc()
        raise SystemExit(1) from exc
    cast(Callable[[], None], cli_main)()
