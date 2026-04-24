# Planning example

Create and plan a task:

```bash
taskledger task create parser-fix --description "Repair parser handling."
taskledger plan start parser-fix
taskledger question add parser-fix --text "Should legacy storage be removed?"
taskledger plan propose parser-fix --file ./plan.md
```
