# Validation example

Validate a finished implementation:

```bash
taskledger context --for validation --format markdown
taskledger validate start
taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_parser.py"
taskledger validate finish --result passed --summary "Validated parser changes."
```
