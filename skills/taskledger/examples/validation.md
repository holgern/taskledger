# Validation example

Complete validation of a finished implementation with status checks and waiver handling:

```bash
# Step 1: Get validation context for fresh start
taskledger context --for validation --format markdown

# Step 2: Start the validation run
taskledger validate start

# Step 3: Check current validation status and identify blockers
taskledger validate status

# Step 4: Run verification checks and record criterion results
taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_parser.py"
taskledger validate check --criterion ac-0002 --status pass --evidence "Code review by Alice"
taskledger validate check --criterion ac-0003 --status fail --evidence "Integration test failed in staging"

# Step 5: Waive non-critical criteria if authorized
taskledger validate waive --criterion ac-0003 --reason "Issue tracked in JIRA-1234, will fix in next release"

# Step 6: Verify all mandatory criteria now pass
taskledger validate status

# Step 7: Finish validation
taskledger validate finish --result passed --summary "Implementation validated against all acceptance criteria with authorized waiver for ac-0003."
```

## Recovery

If validation fails and needs to return to implementation:

```bash
taskledger validate finish --result failed --summary "Parser implementation does not handle edge cases correctly."
taskledger handoff implementation-context --format markdown  # Prepare context for next implementation attempt
```
