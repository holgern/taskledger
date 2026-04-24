# Implementation example

Implement an approved task:

```bash
taskledger handoff implementation-context parser-fix --format markdown
taskledger implement start parser-fix
taskledger implement log parser-fix --message "Reworked parser entrypoint."
taskledger implement add-change parser-fix --path taskledger/parser.py --kind edit --summary "Normalized parser fallback behavior."
taskledger implement finish parser-fix --summary "Implemented the approved parser changes."
```
