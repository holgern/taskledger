# Implementation example

Implement an approved task:

```bash
taskledger context --for implementation --format markdown
taskledger implement start
taskledger implement log --message "Reworked parser entrypoint."
taskledger implement change --path taskledger/parser.py --kind edit --summary "Normalized parser fallback behavior."
taskledger implement finish --summary "Implemented the approved parser changes."
```
