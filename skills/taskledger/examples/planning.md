# Planning example

Create and plan a task:

```bash
taskledger task new "Parser fix" --slug parser-fix --description "Repair parser handling."
taskledger actor whoami
taskledger plan start
taskledger question add --text "Should legacy storage be removed?" --required-for-plan
taskledger question answer q-0001 --text "No." --actor user
taskledger question status
taskledger question answers
taskledger plan regenerate --from-answers --file ./plan.md
```
