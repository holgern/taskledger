from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _init(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _prepare_validating_task(tmp_path: Path) -> None:
    _init(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "validation-gate",
                "--description",
                "Exercise validation gates.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "propose", "--task", "validation-gate",
                "--criterion",
                "Mandatory behavior is checked.",
                "--text",
                "## Goal\n\nValidate objectively.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "approve", "--task", "validation-gate",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "implement", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement", "finish", "--task", "validation-gate",
                "--summary",
                "Implemented.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "validate", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )


def _prepare_validating_task_with_mandatory_todo(tmp_path: Path) -> None:
    _init(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "validation-gate",
                "--description",
                "Exercise validation gates.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "propose", "--task", "validation-gate",
                "--criterion",
                "Mandatory behavior is checked.",
                "--text",
                "## Goal\n\nValidate objectively.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "approve", "--task", "validation-gate",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo", "add", "--task", "validation-gate",
                "--text",
                "Final sign-off",
                "--mandatory",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "implement", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement", "finish", "--task", "validation-gate",
                "--summary",
                "Implemented.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "validate", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )


def test_validation_pass_requires_mandatory_criteria_checks(tmp_path: Path) -> None:
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "finish", "--task", "validation-gate",
            "--result",
            "passed",
            "--summary",
            "No checks recorded.",
        ],
    )

    payload = _json(result)
    assert result.exit_code == 7
    assert payload["error"]["code"] == "VALIDATION_INCOMPLETE"
    assert payload["error"]["details"]["missing_criteria"] == ["ac-0001"]


def test_validation_pass_accepts_canonical_criterion_check(tmp_path: Path) -> None:
    _prepare_validating_task(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate", "check", "--task", "validation-gate",
                "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "pytest -q",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "finish", "--task", "validation-gate",
            "--result",
            "passed",
            "--summary",
            "All gates passed.",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert _json(result)["result"]["status"] == "done"


def test_context_dossier_and_link_alias_are_canonical(tmp_path: Path) -> None:
    _init(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "context-task",
                "--description",
                "Render context.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "file",
                "add",
                "--task",
                "context-task",
                "--path",
                "README.md",
                "--kind",
                "doc",
            ],
        ).exit_code
        == 0
    )

    context = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "context",
            "--task",
            "context-task",
            "--for",
            "planning",
            "--format",
            "markdown",
        ],
    )
    assert context.exit_code == 0
    assert "Planning Context" in context.stdout
    assert "@README.md" in context.stdout

    dossier = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "dossier",
            "--task",
            "context-task",
            "--format",
            "markdown",
        ],
    )
    assert dossier.exit_code == 0
    assert "Task Dossier" in dossier.stdout


def test_user_dependency_waiver_unblocks_implementation(tmp_path: Path) -> None:
    _init(tmp_path)
    for slug in ("dependency", "main-task"):
        assert (
            runner.invoke(
                app,
                [
                    "--cwd",
                    str(tmp_path),
                    "task",
                    "create",
                    slug,
                    "--description",
                    slug,
                ],
            ).exit_code
            == 0
        )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "require", "add", "dependency", "--task", "main-task"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "main-task"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "propose", "--task", "main-task",
                "--criterion",
                "Implementation starts.",
                "--text",
                "## Goal\n\nStart implementation.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "approve", "--task", "main-task",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )

    blocked = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "implement", "start", "--task", "main-task"],
    )
    assert blocked.exit_code == 3

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "require", "waive", "dependency", "--task", "main-task",
                "--actor",
                "user",
                "--reason",
                "Safe to proceed.",
            ],
        ).exit_code
        == 0
    )
    allowed = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "implement", "start", "--task", "main-task"],
    )
    assert allowed.exit_code == 0, allowed.stdout


def test_services_tasks_has_no_duplicate_top_level_function_names() -> None:
    """Static AST check: no duplicate top-level function definitions."""
    import ast

    path = Path(__file__).resolve().parents[1] / "taskledger" / "services" / "tasks.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    seen: set[str] = set()
    duplicates: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name in seen:
                duplicates.add(node.name)
            seen.add(node.name)

    assert duplicates == set(), f"Duplicate top-level functions: {duplicates}"


def test_import_smoke_tests() -> None:
    """Smoke tests for module imports."""
    from taskledger.domain.policies import Decision, PolicyDecision

    assert Decision is not None
    assert PolicyDecision is not None
    assert PolicyDecision is Decision

    decision = Decision(allowed=True, code="OK", message="Test message")
    assert decision.ok is True
    assert decision.reason == "Test message"


def test_taskledger_main_import() -> None:
    """Verify taskledger can be imported as a package."""
    import taskledger

    assert taskledger is not None


def test_resolve_criterion_ref_canonicalization(tmp_path: Path) -> None:
    """Test criterion reference canonicalization."""
    from taskledger.domain.models import AcceptanceCriterion, PlanRecord
    from taskledger.services.tasks import _resolve_criterion_ref

    plan = PlanRecord(
        task_id="test-task",
        plan_version=1,
        body="Test plan",
        criteria=(
            AcceptanceCriterion(id="ac-0001", text="First criterion", mandatory=True),
            AcceptanceCriterion(id="ac-0002", text="Second criterion", mandatory=True),
        ),
    )

    assert _resolve_criterion_ref(plan, "ac-0001") == "ac-0001"
    assert _resolve_criterion_ref(plan, "AC-0001") == "ac-0001"
    assert _resolve_criterion_ref(plan, "ac-1") == "ac-0001"
    assert _resolve_criterion_ref(plan, "1") == "ac-0001"

    assert _resolve_criterion_ref(plan, "ac-0002") == "ac-0002"
    assert _resolve_criterion_ref(plan, "AC-0002") == "ac-0002"
    assert _resolve_criterion_ref(plan, "ac-2") == "ac-0002"
    assert _resolve_criterion_ref(plan, "2") == "ac-0002"


def test_resolve_criterion_ref_unknown(tmp_path: Path) -> None:
    """Test criterion resolver with unknown reference."""
    from taskledger.domain.models import AcceptanceCriterion, PlanRecord
    from taskledger.errors import LaunchError
    from taskledger.services.tasks import _resolve_criterion_ref

    plan = PlanRecord(
        task_id="test-task",
        plan_version=1,
        body="Test plan",
        criteria=(
            AcceptanceCriterion(id="ac-0001", text="First criterion", mandatory=True),
        ),
    )

    try:
        _resolve_criterion_ref(plan, "ac-9999")
        raise AssertionError("Should have raised LaunchError")
    except LaunchError as e:
        assert "Unknown acceptance criterion" in str(e)
        assert "ac-9999" in str(e)
        assert "ac-0001" in str(e)


def test_reject_unknown_criterion_at_check_time(tmp_path: Path) -> None:
    """Test that unknown criterion is rejected when recording a check."""
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate", "check", "--task", "validation-gate",
            "--criterion",
            "ac-9999",
            "--status",
            "pass",
            "--evidence",
            "pytest",
        ],
    )
    assert result.exit_code != 0
    assert (
        "Unknown acceptance criterion" in result.stdout
        or "Unknown acceptance criterion" in result.stderr
    )


def test_latest_check_wins_semantics(tmp_path: Path) -> None:
    """Test that latest check per criterion determines
    pass eligibility (not history)."""
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate", "check", "--task", "validation-gate",
            "--criterion",
            "ac-0001",
            "--status",
            "fail",
            "--evidence",
            "first run failed",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate", "check", "--task", "validation-gate",
            "--criterion",
            "ac-0001",
            "--status",
            "pass",
            "--evidence",
            "fixed and reran",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "finish", "--task", "validation-gate",
            "--result",
            "passed",
            "--summary",
            "Ready to pass.",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["result"]["status"] == "done"


def test_waiver_satisfies_criterion(tmp_path: Path) -> None:
    """Test that user can waive a criterion to satisfy mandatory gate."""
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate", "waive", "--task", "validation-gate",
            "--criterion",
            "ac-0001",
            "--reason",
            "Safe to proceed with waiver.",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "finish", "--task", "validation-gate",
            "--result",
            "passed",
            "--summary",
            "Criterion waived.",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["result"]["status"] == "done"


def test_validation_status_command_shows_blockers(tmp_path: Path) -> None:
    """Test validate status command renders blockers."""
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "status", "--task", "validation-gate",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    status_result = data["result"].get("result", {})
    assert not status_result.get("can_finish_passed", False)
    blockers = status_result.get("blockers", [])
    assert len(blockers) > 0
    assert any(b.get("kind") == "criterion_missing" for b in blockers)


def test_mandatory_todo_blocks_validation_completion(tmp_path: Path) -> None:
    """Test that open mandatory todos block validation completion."""
    _init(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "validation-gate",
                "--description",
                "Exercise validation gates.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "propose", "--task", "validation-gate",
                "--criterion",
                "Mandatory behavior is checked.",
                "--text",
                "## Goal\n\nValidate objectively.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "approve", "--task", "validation-gate",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )

    # Add mandatory todo during plan phase (before implement starts)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo", "add", "--task", "validation-gate",
                "--text",
                "Final sign-off",
                "--mandatory",
            ],
        ).exit_code
        == 0
    )

    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "implement", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement", "finish", "--task", "validation-gate",
                "--summary",
                "Implemented.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "validate", "start", "--task", "validation-gate"]
        ).exit_code
        == 0
    )

    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate", "check", "--task", "validation-gate",
            "--criterion",
            "ac-0001",
            "--status",
            "pass",
            "--evidence",
            "pytest -q",
        ],
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate", "finish", "--task", "validation-gate",
            "--result",
            "passed",
            "--summary",
            "Ready.",
        ],
    )
    assert result.exit_code == 7
    payload = _json(result)
    assert payload["error"]["code"] == "VALIDATION_INCOMPLETE"
    assert len(payload["error"]["details"].get("open_mandatory_todos", [])) > 0


def test_next_action_validation_includes_blockers(tmp_path: Path) -> None:
    """Test that next-action reports validation blockers when stage is validation."""
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "next-action", "--task", "validation-gate",
        ],
    )
    assert result.exit_code == 0
    data = _json(result)
    assert data["result"]["action"] == "validate-finish"
    assert len(data["result"].get("blocking", [])) > 0
    assert any(
        b.get("kind") == "criterion_missing" for b in data["result"].get("blocking", [])
    )
