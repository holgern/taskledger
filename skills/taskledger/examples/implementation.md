# Implementation example

Implement an approved task:

```bash
taskledger context parser-fix --for implementation --format markdown
taskledger implement start parser-fix
taskledger implement log parser-fix --message "Reworked parser entrypoint."
taskledger implement change parser-fix --path taskledger/parser.py --kind edit --summary "Normalized parser fallback behavior."
taskledger implement finish parser-fix --summary "Implemented the approved parser changes."
```
