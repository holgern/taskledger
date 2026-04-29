from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.domain.states import EXIT_CODE_VALIDATION_FAILED


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0, result.output


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _create_task(tmp_path: Path, slug: str = "lint-task") -> None:
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "create", slug, "--description", "lint test"],
    )
    assert result.exit_code == 0, result.output


def _start_planning(tmp_path: Path, slug: str = "lint-task") -> None:
    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "plan", "start", "--task", slug]
    )
    assert result.exit_code == 0, result.output


def _propose_plan(
    tmp_path: Path,
    plan_text: str,
    slug: str = "lint-task",
) -> None:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "propose",
            "--task",
            slug,
            "--text",
            plan_text,
        ],
    )
    assert result.exit_code == 0, result.output


def _add_and_answer_required_question(
    tmp_path: Path,
    slug: str,
    answer: str = "PostgreSQL.",
) -> None:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "question",
            "add",
            "--task",
            slug,
            "--text",
            "Which database?",
            "--required-for-plan",
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "question",
            "answer",
            "--task",
            slug,
            "q-0001",
            "--text",
            answer,
        ],
    )
    assert result.exit_code == 0, result.output


# Full plan with all required fields
_FULL_PLAN = """\
---
goal: Test goal for plan linting.
files:
  - taskledger/services/plan_lint.py
test_commands:
  - pytest tests/test_plan_lint.py
expected_outputs:
  - pytest exits 0
acceptance_criteria:
  - id: ac-0001
    text: Lint command reports issues correctly.
todos:
  - text: Create `taskledger/services/plan_lint.py` with lint rules.
    validation_hint: pytest tests/test_plan_lint.py
---

## Goal

Test goal for plan linting.
"""

# Plan missing goal
_NO_GOAL_PLAN = """\
---
acceptance_criteria:
  - id: ac-0001
    text: Some criterion.
todos:
  - text: Add lint_service.py with lint_plan function.
---

## Steps

Do the work.
"""

# Plan missing criteria
_NO_CRITERIA_PLAN = """\
---
goal: Fix something.
todos:
  - text: Add lint_service.py with lint_plan function.
---

## Steps

Do the work.
"""

# Plan missing todos
_NO_TODOS_PLAN = """\
---
goal: Fix something.
acceptance_criteria:
  - id: ac-0001
    text: Some criterion.
---

## Steps

Do the work.
"""

# Plan with todo waiver
_WAIVED_TODOS_PLAN = """\
---
goal: Fix something.
todos_waived_reason: "No checklist needed for docs-only correction."
acceptance_criteria:
  - id: ac-0001
    text: Some criterion.
---

## Steps

Do the work.
"""

# Plan with vague todo
_VAGUE_TODO_PLAN = """\
---
goal: Fix something.
acceptance_criteria:
  - id: ac-0001
    text: Some criterion.
todos:
  - fix tests
---

## Steps

Do the work.
"""

# Plan with placeholders
_PLACEHOLDER_PLAN = """\
---
goal: Fix something TBD.
acceptance_criteria:
  - id: ac-0001
    text: Some criterion.
todos:
  - text: Add lint_service.py with appropriate tests.
    validation_hint: pytest tests/test_plan_lint.py
---

## Steps

Do the work later.
"""

_NO_TODO_HINTS_PLAN = """\
---
goal: Wire compact execution hints.
files:
  - taskledger/services/plan_lint.py
expected_outputs:
  - plan lint emits a warning
acceptance_criteria:
  - id: ac-0001
    text: A warning is emitted.
todos:
  - text: Update `taskledger/services/plan_lint.py` to emit a warning.
---

## Goal

Wire compact execution hints.
"""


class TestPlanLintPasses:
    def test_plan_lint_passes_for_executable_plan(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "lint-pass")
        _start_planning(tmp_path, "lint-pass")
        _propose_plan(tmp_path, _FULL_PLAN, slug="lint-pass")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "lint", "--task", "lint-pass"],
        )
        assert result.exit_code == 0, result.output
        payload = _json(result)
        assert payload["ok"] is True
        res = payload["result"]
        assert isinstance(res, dict)
        assert res["kind"] == "plan_lint"
        assert res["passed"] is True
        assert res["plan_version"] == 1
        summary = res["summary"]
        assert isinstance(summary, dict)
        assert summary["errors"] == 0

    def test_plan_template_prints_stdout_when_no_file(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "template-stdout")
        _start_planning(tmp_path, "template-stdout")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "template", "--task", "template-stdout"],
        )

        assert result.exit_code == 0, result.output
        assert result.stdout.startswith("---\n")
        assert "acceptance_criteria:" in result.stdout

    def test_plan_template_from_answers_writes_file(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "template-file")
        _start_planning(tmp_path, "template-file")
        _add_and_answer_required_question(tmp_path, "template-file")
        plan_path = tmp_path / "plan.md"

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "template",
                "--task",
                "template-file",
                "--from-answers",
                "--file",
                str(plan_path),
            ],
        )

        assert result.exit_code == 0, result.output
        contents = plan_path.read_text(encoding="utf-8")
        assert "## Notes from answered questions" in contents
        assert "- q-0001: PostgreSQL." in contents

    def test_filled_plan_template_passes_lint(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "template-lint")
        _start_planning(tmp_path, "template-lint")
        _add_and_answer_required_question(tmp_path, "template-lint")
        plan_path = tmp_path / "plan.md"

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "template",
                "--task",
                "template-lint",
                "--from-answers",
                "--file",
                str(plan_path),
            ],
        )
        assert result.exit_code == 0, result.output

        contents = plan_path.read_text(encoding="utf-8")
        contents = contents.replace(
            "<one sentence describing the desired outcome>",
            "Implement PostgreSQL-only behavior.",
        )
        contents = contents.replace("@path/to/file.py", "taskledger/services/tasks.py")
        contents = contents.replace(
            "pytest -q path/to/test_file.py",
            "pytest -q tests/test_plan_lint.py",
        )
        contents = contents.replace(
            "<observable acceptance criterion>",
            (
                "The template-based plan can be linted after concrete values are "
                "filled in."
            ),
        )
        contents = contents.replace(
            "<specific behavior>",
            "the PostgreSQL-only planning behavior",
        )
        contents = contents.replace(
            "<repeat or expand the goal in human prose>",
            (
                "Implement PostgreSQL-only behavior and keep the answered planning "
                "context visible."
            ),
        )
        plan_path.write_text(contents, encoding="utf-8")

        upserted = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "upsert",
                "--task",
                "template-lint",
                "--from-answers",
                "--file",
                str(plan_path),
            ],
        )
        assert upserted.exit_code == 0, upserted.output

        linted = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "template-lint",
            ],
        )
        assert linted.exit_code == 0, linted.output
        assert _json(linted)["result"]["passed"] is True


class TestPlanLintErrors:
    def test_plan_lint_reports_missing_goal(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "no-goal")
        _start_planning(tmp_path, "no-goal")
        _propose_plan(tmp_path, _NO_GOAL_PLAN, slug="no-goal")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "no-goal",
                "--version",
                "1",
            ],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        assert res["passed"] is False
        codes = [i["code"] for i in res["issues"]]
        assert "missing_goal" in codes
        goal_issues = [i for i in res["issues"] if i["code"] == "missing_goal"]
        assert goal_issues[0]["severity"] == "error"

    def test_plan_lint_reports_missing_criteria(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "no-criteria")
        _start_planning(tmp_path, "no-criteria")
        _propose_plan(tmp_path, _NO_CRITERIA_PLAN, slug="no-criteria")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "no-criteria",
            ],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        assert res["passed"] is False
        codes = [i["code"] for i in res["issues"]]
        assert "missing_acceptance_criteria" in codes

    def test_plan_lint_reports_missing_todos(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "no-todos")
        _start_planning(tmp_path, "no-todos")
        _propose_plan(tmp_path, _NO_TODOS_PLAN, slug="no-todos")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "no-todos",
            ],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        assert res["passed"] is False
        codes = [i["code"] for i in res["issues"]]
        assert "missing_todos" in codes

    def test_plan_lint_allows_todo_waiver_reason(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "waived")
        _start_planning(tmp_path, "waived")
        _propose_plan(tmp_path, _WAIVED_TODOS_PLAN, slug="waived")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "lint", "--task", "waived"],
        )
        assert result.exit_code == 0, result.output
        payload = _json(result)
        res = payload["result"]
        codes = [i["code"] for i in res["issues"]]
        assert "missing_todos" not in codes

    def test_plan_lint_rejects_vague_todo(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "vague")
        _start_planning(tmp_path, "vague")
        _propose_plan(tmp_path, _VAGUE_TODO_PLAN, slug="vague")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "lint", "--task", "vague"],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        codes = [i["code"] for i in res["issues"]]
        assert "todo_not_concrete" in codes


class TestPlanLintWarnings:
    def test_plan_lint_warns_on_placeholders(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "placeholder")
        _start_planning(tmp_path, "placeholder")
        _propose_plan(tmp_path, _PLACEHOLDER_PLAN, slug="placeholder")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "placeholder",
            ],
        )
        # Warnings only, no strict: should exit 0
        assert result.exit_code == 0, result.output
        payload = _json(result)
        res = payload["result"]
        placeholder_issues = [i for i in res["issues"] if i["code"] == "placeholder"]
        assert len(placeholder_issues) >= 1
        assert placeholder_issues[0]["severity"] == "warning"

    def test_plan_lint_strict_fails_on_placeholders(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "strict-ph")
        _start_planning(tmp_path, "strict-ph")
        _propose_plan(tmp_path, _PLACEHOLDER_PLAN, slug="strict-ph")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "strict-ph",
                "--strict",
            ],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        assert res["passed"] is False
        placeholder_issues = [i for i in res["issues"] if i["code"] == "placeholder"]
        assert len(placeholder_issues) >= 1
        assert placeholder_issues[0]["severity"] == "error"

    def test_plan_lint_warns_when_todos_lack_validation_hints_and_no_tests(
        self, tmp_path: Path
    ) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "todo-hints")
        _start_planning(tmp_path, "todo-hints")
        _propose_plan(tmp_path, _NO_TODO_HINTS_PLAN, slug="todo-hints")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "lint", "--task", "todo-hints"],
        )
        assert result.exit_code == 0, result.output
        payload = _json(result)
        res = payload["result"]
        hint_issues = [
            issue
            for issue in res["issues"]
            if issue["code"] == "missing_todo_validation_hint"
        ]
        assert len(hint_issues) == 1
        assert hint_issues[0]["severity"] == "warning"

    def test_plan_lint_strict_errors_when_todos_lack_validation_hints_and_no_tests(
        self, tmp_path: Path
    ) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "todo-hints-strict")
        _start_planning(tmp_path, "todo-hints-strict")
        _propose_plan(tmp_path, _NO_TODO_HINTS_PLAN, slug="todo-hints-strict")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "lint",
                "--task",
                "todo-hints-strict",
                "--strict",
            ],
        )
        assert result.exit_code == EXIT_CODE_VALIDATION_FAILED
        payload = _json(result)
        res = payload["result"]
        hint_issues = [
            issue
            for issue in res["issues"]
            if issue["code"] == "missing_todo_validation_hint"
        ]
        assert len(hint_issues) == 1
        assert hint_issues[0]["severity"] == "error"


class TestPlanLintVersioning:
    def test_plan_lint_defaults_to_latest_plan(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "multi")
        _start_planning(tmp_path, "multi")
        _propose_plan(tmp_path, _NO_GOAL_PLAN, slug="multi")

        # Propose a second plan via another planning cycle
        _start_planning(tmp_path, "multi")
        _propose_plan(tmp_path, _FULL_PLAN, slug="multi")

        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "lint", "--task", "multi"],
        )
        assert result.exit_code == 0, result.output
        payload = _json(result)
        res = payload["result"]
        assert res["plan_version"] == 2


class TestPlanLintApprovalGate:
    def test_plan_approval_blocks_lint_errors(self, tmp_path: Path) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "gate-block")
        _start_planning(tmp_path, "gate-block")
        _propose_plan(tmp_path, _NO_GOAL_PLAN, slug="gate-block")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "approved",
                "--task",
                "gate-block",
            ],
        )
        assert result.exit_code != 0
        output = result.output
        assert "lint" in output.lower() or "LINT" in output

    def test_plan_approval_lint_escape_hatch_requires_reason(
        self, tmp_path: Path
    ) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "gate-reason")
        _start_planning(tmp_path, "gate-reason")
        _propose_plan(tmp_path, _NO_GOAL_PLAN, slug="gate-reason")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "approved",
                "--allow-lint-errors",
                "--task",
                "gate-reason",
            ],
        )
        assert result.exit_code != 0
        assert "reason" in result.output.lower()

    def test_plan_approval_lint_escape_hatch_succeeds_with_reason(
        self, tmp_path: Path
    ) -> None:
        _init_project(tmp_path)
        _create_task(tmp_path, "gate-ok")
        _start_planning(tmp_path, "gate-ok")
        _propose_plan(tmp_path, _NO_GOAL_PLAN, slug="gate-ok")

        result = runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "approved",
                "--allow-lint-errors",
                "--reason",
                "user accepted rough plan",
                "--task",
                "gate-ok",
            ],
        )
        assert result.exit_code == 0, result.output
