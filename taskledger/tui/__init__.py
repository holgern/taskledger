"""taskledger TUI (optional, requires textual).

The ``taskledger.tui`` package is imported lazily by the ``tui`` CLI command.
Importing :mod:`taskledger.tui.app` triggers textual imports. The CLI never
imports this module at process start; that keeps ``taskledger --help`` free of
the textual dependency.
"""
