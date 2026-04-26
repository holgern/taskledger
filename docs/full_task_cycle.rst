Full Task Cycle
===============

This page shows one complete taskledger cycle, from a fresh task through
planning, questions, implementation, validation, and closure. It uses the
strict task-first command grammar:

.. code-block:: text

   taskledger [--root PATH] [--json] <area> <verb> [RESOURCE_REF] [--task TASK_REF] [options]

The examples assume the task is the active task after creation. If another task
is active, add ``--task parser-fix`` to each task-scoped command.

1. Initialize The Ledger
------------------------

Run this once per workspace:

.. code-block:: bash

   taskledger init
   taskledger doctor
   taskledger status --full

``init`` creates ``.taskledger/``. ``doctor`` checks integrity. ``status --full``
shows the current task, counts, health, and lock state.

2. Create And Activate A Task
-----------------------------

Create the task, then make it active:

.. code-block:: bash

   taskledger task create "Fix parser edge case" --slug parser-fix --description "Repair parser handling for nested expressions."
   taskledger task activate parser-fix --reason "Start parser fix"
   taskledger task active
   taskledger next-action

``task create`` records the task but does not implicitly activate it. Active task
selection is explicit so agents can safely switch between tasks.

Optional setup commands are useful when the task depends on context outside the
description:

.. code-block:: bash

   taskledger intro create "Parser architecture" --text "The parser is staged into tokenize, parse, and normalize passes."
   taskledger intro link intro-0001
   taskledger file add --path taskledger/parser.py --kind code --label "Parser implementation"
   taskledger file add --path tests/test_parser.py --kind test --required-for-validation
   taskledger link add --url https://example.invalid/ticket/123 --label "Support ticket"

Introductions are reusable background notes. File links and external links tell
future planning, implementation, and validation agents where important context
lives.

3. Start Planning
-----------------

Start the planning stage and inspect planning context:

.. code-block:: bash

   taskledger can plan
   taskledger plan start
   taskledger context --for planning --format markdown
   taskledger handoff plan-context --format markdown

``plan start`` acquires a visible planning lock. The context commands render the
current task, linked files, questions, requirements, and prior records.

4. Ask And Answer Questions
---------------------------

Questions capture missing decisions before approval:

.. code-block:: bash

   taskledger question add --text "Should the parser reject or normalize unmatched delimiters?" --required-for-plan
   taskledger question add --text "Which files must validation cover?"
   taskledger question open
   taskledger question answer QUESTION_ID --text "Reject unmatched delimiters with a clear parse error."
   taskledger question dismiss QUESTION_ID --reason "Validation files are already linked."
   taskledger question status
   taskledger question answers --format markdown

Use ``question answer`` for decisions that should affect the plan. Use
``question dismiss`` when the question is no longer relevant.

5. Propose A Plan
-----------------

Write the plan body in a Markdown file and propose it:

.. code-block:: bash

   taskledger plan draft
   taskledger plan propose --file ./plan.md --criterion "Parser rejects unmatched delimiters." --criterion "Regression tests cover nested expressions."
   taskledger plan show --version 1
   taskledger plan diff --from 1 --to 1

``plan propose`` ends the active planning run and creates a reviewable plan
version. Acceptance criteria become validation criteria such as ``ac-0001``.

If answers changed after the plan was proposed, regenerate before approval:

.. code-block:: bash

   taskledger question answer QUESTION_ID --text "Reject unmatched delimiters and keep the original token offset."
   taskledger plan regenerate --from-answers --file ./plan-v2.md
   taskledger plan show --version 2

Regeneration keeps the durable answer snapshot aligned with the plan.

6. Materialize Todos And Approve
--------------------------------

Plans can include todos in front matter, or todos can be added manually. Approval
may also materialize structured plan todos:

.. code-block:: bash

   taskledger plan materialize-todos --version 2 --dry-run
   taskledger plan approve --version 2 --actor user --note "Ready to implement." --reason "Questions answered."
   taskledger todo list
   taskledger todo add --text "Add parser regression tests." --mandatory
   taskledger todo add --text "Update parser error message docs." --optional
   taskledger todo status

Mandatory todos gate implementation completion. Optional todos remain visible but
do not block ``implement finish``.

7. Start Implementation
-----------------------

Begin implementation and keep durable notes as work progresses:

.. code-block:: bash

   taskledger can implement
   taskledger context --for implementation --format markdown
   taskledger implement start
   taskledger implement checklist
   taskledger implement log --message "Started parser fix."
   taskledger implement command -- pytest tests/test_parser.py -q
   taskledger implement change --path taskledger/parser.py --kind edit --summary "Reject unmatched delimiters with source offsets."
   taskledger implement change --path tests/test_parser.py --kind test --summary "Added nested expression and delimiter regression tests."
   taskledger implement deviation --message "Kept tokenizer unchanged because parser-level validation is sufficient."
   taskledger implement artifact --path .taskledger-artifacts/parser-test-output.txt --summary "Parser regression test output."
   taskledger implement scan-changes --from-git --summary "Implementation diff summary."
   taskledger implement status

Use ``implement command`` when you want taskledger to record a command run as
part of implementation. Use ``implement deviation`` when the implementation
differs from the approved plan.

8. Complete Implementation Todos
--------------------------------

Mark mandatory todos done with evidence:

.. code-block:: bash

   taskledger todo next
   taskledger todo done TODO_ID --evidence "pytest tests/test_parser.py -q" --artifact .taskledger-artifacts/parser-test-output.txt
   taskledger todo done TODO_ID --evidence "Reviewed parser docs."
   taskledger todo status
   taskledger implement finish --summary "Implemented parser delimiter rejection and tests."

``implement finish`` releases the implementation lock only when mandatory todos
are complete.

9. Validate The Work
--------------------

Start validation, run checks against each acceptance criterion, and finish the
validation stage:

.. code-block:: bash

   taskledger can validate
   taskledger context --for validation --format markdown
   taskledger validate start
   taskledger validate status
   taskledger validate check --criterion ac-0001 --status pass --evidence "pytest tests/test_parser.py -q"
   taskledger validate check --criterion ac-0002 --status pass --evidence "pytest tests/test_parser.py -q"
   taskledger validate show
   taskledger validate finish --result passed --summary "Parser fix validated with regression tests."

If a criterion is intentionally not validated, a user can waive it:

.. code-block:: bash

   taskledger validate waive --criterion ac-0003 --reason "Covered by upstream integration test." --actor user

Waivers should be rare and explicit.

10. Close The Task
------------------

After validation passes, close the task and inspect final state:

.. code-block:: bash

   taskledger task dossier --format markdown
   taskledger handoff create --mode validation --summary "Parser fix is implemented and validated."
   taskledger handoff show HANDOFF_ID --format text
   taskledger task close --summary "Fixed parser delimiter handling and validated parser regressions."
   taskledger task show
   taskledger status --full
   taskledger doctor

``task close`` marks the task done. The dossier and handoff commands preserve a
fresh-context summary for future agents or reviewers.

11. Recovery And Maintenance Commands
-------------------------------------

These commands are not part of the happy path, but they complete the operational
cycle:

.. code-block:: bash

   taskledger lock show
   taskledger doctor locks
   taskledger lock break --reason "Recover stale planning lock."
   taskledger repair index
   taskledger repair task --reason "Inspect task record after manual edit."
   taskledger reindex
   taskledger --json export
   taskledger snapshot ./taskledger-snapshot --include-bodies --include-run-artifacts

Locks are never cleared silently. Use ``lock break`` only after inspecting the
lock and recording a reason.
