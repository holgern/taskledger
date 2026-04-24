# Planning example

Create and plan a task:

```bash
taskledger task create parser-fix --description "Repair parser handling."
taskledger task activate parser-fix
taskledger plan start
taskledger question add --text "Should legacy storage be removed?"
taskledger plan propose --file ./plan.md
```
