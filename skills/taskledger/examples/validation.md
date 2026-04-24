# Validation example

Validate a finished implementation:

```bash
taskledger handoff validation-context parser-fix --format markdown
taskledger validate start parser-fix
taskledger validate add-check parser-fix --name "pytest -q" --status pass --details "Targeted tests passed" --evidence "pytest -q tests/test_parser.py"
taskledger validate finish parser-fix --result passed --summary "Validated parser changes."
```
