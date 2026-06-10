"""Tests for BDD CLI commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from taskledger.cli import app
from tests.support.builders import create_approved_task, init_workspace

runner = CliRunner()


class TestBddInit:
    def test_bdd_init_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(
            app, ["--json", "bdd", "init", "--feature", "Task lifecycle gates"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["command"] == "bdd.init"
        assert payload["result"]["feature"]["title"] == "Task lifecycle gates"

    def test_bdd_init_human(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        result = runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        assert result.exit_code == 0
        assert "BDD initialized" in result.stdout

    def test_bdd_init_twice_fails(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)

        runner.invoke(app, ["bdd", "init", "--feature", "First"])
        result = runner.invoke(app, ["bdd", "init", "--feature", "Second"])
        assert result.exit_code != 0


class TestBddStatus:
    def test_bdd_status_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(app, ["--json", "bdd", "status"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["result"]["feature_title"] == "Test"
        assert payload["result"]["rule_count"] == 0


class TestBddRuleCommands:
    def test_rule_add_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app, ["--json", "bdd", "rule", "add", "Implementation requires plan"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["result"]["rule"]["title"] == "Implementation requires plan"
        assert payload["result"]["rule"]["id"] == "rule-0001"

    def test_rule_list_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(app, ["bdd", "rule", "add", "Rule 1"])
        runner.invoke(app, ["bdd", "rule", "add", "Rule 2"])

        result = runner.invoke(app, ["--json", "bdd", "rule", "list"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert len(payload["result"]["rules"]) == 2

    def test_rule_show_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(app, ["bdd", "rule", "add", "My rule"])

        result = runner.invoke(app, ["--json", "bdd", "rule", "show", "rule-0001"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"]["rule"]["id"] == "rule-0001"


class TestBddExampleCommands:
    def test_example_add_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "add",
                "--title",
                "Test scenario",
                "--given",
                "something",
                "--when",
                "action",
                "--then",
                "result",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        ex = payload["result"]["example"]
        assert ex["title"] == "Test scenario"
        assert ex["status"] == "linked"
        assert ex["acceptance_criteria"] == ["ac-0001"]

    def test_example_list_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Ex1",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        result = runner.invoke(app, ["--json", "bdd", "example", "list"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert len(payload["result"]["examples"]) == 1

    def test_example_show_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Ex1",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        result = runner.invoke(app, ["--json", "bdd", "example", "show", "bdd-0001"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["result"]["example"]["id"] == "bdd-0001"

    def test_example_link_ac(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Ex1",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        result = runner.invoke(
            app, ["--json", "bdd", "example", "link-ac", "bdd-0001", "ac-0001"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert "ac-0001" in payload["result"]["example"]["acceptance_criteria"]
        assert payload["result"]["example"]["status"] == "linked"


class TestBddGherkinExport:
    def test_gherkin_export_json(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test scenario",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        out = str(tmp_path / "test.feature")
        result = runner.invoke(app, ["--json", "bdd", "gherkin-export", "--out", out])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert "bdd-0001" in payload["result"]["exported_examples"]
        assert payload["result"]["warning_details"] == []

    def test_gherkin_export_warns_for_deprecated_paths(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test scenario",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        out = "tests/bdd/features/task-0123-test.feature"
        result = runner.invoke(app, ["--json", "bdd", "gherkin-export", "--out", out])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        warning = payload["result"]["warning_details"][0]
        assert warning["code"] == "TLBDD_PATH_DERIVED_NOT_CANONICAL"
        assert any("tests/bdd/features/" in item for item in warning["reasons"])
        assert any("task-<digits>" in item for item in warning["reasons"])

    def test_export_json_includes_external_behavior_spec_metadata(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        feature_file, pytest_ref = _write_behavior_assets(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Automated scenario",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "link-automation",
                "bdd-0001",
                "--feature-file",
                feature_file,
                "--scenario",
                "@bdd-implementation-blocked-before-plan-acceptance",
                "--pytest",
                pytest_ref,
            ],
        )

        out = str(tmp_path / ".specweave" / "mappings" / "task-0001.bdd.json")
        result = runner.invoke(app, ["--json", "bdd", "export-json", "--out", out])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        export = payload["result"]["export"]
        assert export["kind"] == "task_bdd_spec"
        assert export["external_behavior_specs"][0]["path"] == feature_file
        pytest_tests = export["external_behavior_specs"][0]["pytest_tests"]
        assert pytest_tests[0]["path"] == "tests/test_task_management_plan_gates.py"
        assert pytest_tests[0]["nodeid"] == pytest_ref


class TestBddArchledgerBridge:
    def test_archledger_candidate(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Lifecycle gate test",
                "--given",
                "a task",
                "--when",
                "action",
                "--then",
                "result",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )

        out = str(tmp_path / "candidate.md")
        result = runner.invoke(
            app, ["--json", "bdd", "archledger-candidate", "bdd-0001", "--out", out]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["result"]["candidate"]["suggested_type"] == "runtime_scenario"

    def test_example_link_archledger(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "link-archledger",
                "bdd-0001",
                "al_runtime_0123",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert "al_runtime_0123" in payload["result"]["example"]["archledger_refs"]

    def test_link_automation_then_candidate_includes_feature_file(
        self, tmp_path, monkeypatch
    ) -> None:
        """Recorded spec/test metadata flows into the Archledger candidate."""
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        feature_file, pytest_ref = _write_behavior_assets(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Automated scenario",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )

        link_result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "link-automation",
                "bdd-0001",
                "--feature-file",
                feature_file,
                "--scenario",
                "@bdd-implementation-blocked-before-plan-acceptance",
                "--pytest",
                pytest_ref,
            ],
        )
        assert link_result.exit_code == 0
        example = json.loads(link_result.stdout)["result"]["example"]
        assert example["automation"]["feature_file"] == feature_file
        assert (
            example["automation"]["scenario"]
            == "@bdd-implementation-blocked-before-plan-acceptance"
        )
        assert example["automation"]["pytest_nodeid"] == pytest_ref

        out = str(tmp_path / "candidate.md")
        result = runner.invoke(
            app, ["--json", "bdd", "archledger-candidate", "bdd-0001", "--out", out]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        content = payload["result"]["candidate"]["content"]
        assert feature_file in content
        assert "tests/test_task_management_plan_gates.py" in content
        assert pytest_ref in content
        assert "source_refs:" in content
        assert "test_refs:" in content
        assert "automation:" in content

    def test_link_automation_rejects_non_canonical_feature_path(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Automated scenario",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
            ],
        )

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "link-automation",
                "bdd-0001",
                "--feature-file",
                "tests/bdd/features/test.feature",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert "specs/behavior/features" in payload["error"]["message"]


AC_PLAN = """---
goal: Test goal.
acceptance_criteria:
  - id: ac-0001
    text: Criterion passes.
    mandatory: true
todos:
  - id: todo-0001
    text: Implement it.
    validation_hint: pytest tests
---

# Plan

Test plan.
"""


class TestBddReferenceValidation:
    """Finding 7: rule and acceptance-criterion refs are validated."""

    def test_example_add_unknown_rule_fails(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "add",
                "--title",
                "Bad rule ref",
                "--rule",
                "rule-9999",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "BDD rule not found" in payload["error"]["message"]

    def test_example_add_unknown_criterion_with_accepted_plan_fails(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        init_workspace(tmp_path)
        create_approved_task(tmp_path, plan_text=AC_PLAN)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "add",
                "--title",
                "Bad criterion ref",
                "--given",
                "a",
                "--acceptance-criterion",
                "ac-9999",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "ac-9999 is not in the accepted plan" in payload["error"]["message"]

    def test_example_add_known_criterion_with_accepted_plan_succeeds(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        init_workspace(tmp_path)
        create_approved_task(tmp_path, plan_text=AC_PLAN)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "add",
                "--title",
                "Good criterion ref",
                "--given",
                "a",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        # Strict validation passed: no verification warnings.
        assert payload["result"]["warnings"] == []
        assert payload["result"]["example"]["acceptance_criteria"] == ["ac-0001"]

    def test_example_add_criterion_without_plan_warns(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _init_project(tmp_path)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])

        result = runner.invoke(
            app,
            [
                "--json",
                "bdd",
                "example",
                "add",
                "--title",
                "Early discovery",
                "--given",
                "a",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )
        # Early discovery stays allowed, with a clear warning.
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert any("no accepted plan yet" in w for w in payload["result"]["warnings"])
        assert payload["result"]["example"]["acceptance_criteria"] == ["ac-0001"]

    def test_link_ac_unknown_criterion_with_accepted_plan_fails(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        init_workspace(tmp_path)
        create_approved_task(tmp_path, plan_text=AC_PLAN)
        runner.invoke(app, ["bdd", "init", "--feature", "Test"])
        runner.invoke(
            app,
            ["--json", "bdd", "example", "add", "--title", "No AC", "--given", "a"],
        )

        result = runner.invoke(
            app,
            ["--json", "bdd", "example", "link-ac", "bdd-0001", "ac-9999"],
        )
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "ac-9999 is not in the accepted plan" in payload["error"]["message"]


def _init_project(tmp_path) -> None:
    """Initialize a minimal taskledger project."""
    runner.invoke(app, ["init"])
    # Activate a task for testing
    runner.invoke(app, ["task", "create", "Test task"])
    runner.invoke(app, ["task", "activate", "task-0001"])


def _write_behavior_assets(tmp_path) -> tuple[str, str]:
    feature_rel = "specs/behavior/features/task-management/plan-gates.feature"
    feature_path = tmp_path / feature_rel
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.write_text("Feature: Plan gates\n", encoding="utf-8")

    pytest_rel = "tests/test_task_management_plan_gates.py"
    pytest_path = tmp_path / pytest_rel
    pytest_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_path.write_text(
        "def test_agent_cannot_start_implementation_before_plan_approval():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    pytest_ref = (
        "tests/test_task_management_plan_gates.py::"
        "test_agent_cannot_start_implementation_before_plan_approval"
    )
    return feature_rel, pytest_ref
