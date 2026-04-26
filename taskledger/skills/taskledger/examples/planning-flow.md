# Planning flow

1. `taskledger --root /workspace task create "Rewrite V2" --slug rewrite-v2 --description "Migrate to the task-first design."`
2. `taskledger --root /workspace actor whoami`
3. `taskledger --root /workspace plan start`
4. `taskledger --root /workspace question add --text "Should exports include the new state?" --required-for-plan`
5. The agent stops until the user answers required questions.
6. `taskledger --root /workspace question answer q-0001 --text "Yes." --actor user`
7. `taskledger --root /workspace question status`
8. `taskledger --root /workspace plan regenerate --from-answers --file ./plan.md`
9. `taskledger --root /workspace plan approve --version 1 --actor user --note "Ready."`
