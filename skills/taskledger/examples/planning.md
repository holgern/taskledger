# Planning example

Create and plan a task:

```bash
taskledger task create "Parser fix" --slug parser-fix --description "Repair parser handling."
taskledger task activate parser-fix --reason "Start planning"
taskledger actor whoami
taskledger plan start
taskledger question add --text "Should legacy storage be removed?" --required-for-plan
taskledger question answer-many --text "q-0001: No." --actor user
taskledger question status
taskledger question answers
taskledger plan upsert --from-answers --file ./plan.md
```
