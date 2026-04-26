# Planning flow

1. `taskledger --root /workspace task create "Rewrite V2" --slug rewrite-v2 --description "Migrate to the task-first design."`
2. `taskledger --root /workspace task activate rewrite-v2 --reason "Start planning"`
3. `taskledger --root /workspace actor whoami`
4. `taskledger --root /workspace plan start`
5. `taskledger --root /workspace question add --text "Should exports include the new state?" --required-for-plan`
6. The agent asks the question in harness chat and stops until the user answers.
7. `taskledger --root /workspace question answer-many --text "q-0001: Yes." --actor user`
8. `taskledger --root /workspace question status`
9. `taskledger --root /workspace question answers`
10. `taskledger --root /workspace plan upsert --from-answers --file ./plan.md`
11. `taskledger --root /workspace plan accept --version 1 --note "Ready."`
