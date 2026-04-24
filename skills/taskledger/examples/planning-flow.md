# Planning flow

1. `taskledger --root /workspace task create rewrite-v2 --title "Rewrite V2" --description "Migrate to the task-first design."`
2. `taskledger --root /workspace plan start rewrite-v2`
3. `taskledger --root /workspace question add rewrite-v2 --text "Should exports include the new state?"`
4. Answer or dismiss every open planning question.
5. `taskledger --root /workspace plan propose rewrite-v2 --file ./plan.md`
6. `taskledger --root /workspace plan approve rewrite-v2 --version 1`
