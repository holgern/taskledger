# Planning flow

1. `taskledger --root /workspace task create rewrite-v2 --title "Rewrite V2" --description "Migrate to the task-first design."`
2. `taskledger --root /workspace task activate rewrite-v2`
3. `taskledger --root /workspace plan start`
4. `taskledger --root /workspace question add --text "Should exports include the new state?"`
5. Answer or dismiss every open planning question.
6. `taskledger --root /workspace plan propose --file ./plan.md`
7. `taskledger --root /workspace plan approve --version 1 --actor user --note "Ready."`
