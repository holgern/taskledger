# Validation example

Validate a finished implementation:

```bash
taskledger context parser-fix --for validation --format markdown
taskledger validate start parser-fix
taskledger validate check parser-fix --criterion ac-0001 --status pass --evidence "pytest -q tests/test_parser.py"
taskledger validate finish parser-fix --result passed --summary "Validated parser changes."
```
