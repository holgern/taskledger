"""Tests for todo-based implementation finish gate.

Verifies that implement finish is blocked until all todos are done,
and that todos properly track completion status.
"""

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


def _prepare_task_for_implementation(tmp_path: Path, task_id: str = "test-task") -> None:
    """Create, plan, approve, and start implementing a task."""
    _init(tmp_path)
    
    # Create task
    assert runner.invoke(
        app,
        [
            "--cwd", str(tmp_path),
            "task", "create", task_id,
            "--description", "Test task for todo gate.",
        ],
    ).exit_code == 0
    
    # Start planning
    assert runner.invoke(
        app,
        ["--cwd", str(tmp_path), "plan", "start", task_id],
    ).exit_code == 0
    
    # Propose plan
    assert runner.invoke(
        app,
        [
            "--cwd", str(tmp_path),
            "plan", "propose", task_id,
            "--criterion", "Works correctly.",
            "--text", "## Implementation Plan\n\nImplement the feature.",
        ],
    ).exit_code == 0
    
    # Approve plan
    assert runner.invoke(
        app,
        [
            "--cwd", str(tmp_path),
            "plan", "approve", task_id,
            "--version", "1",
            "--actor", "user",
            "--note", "Looks good.",
        ],
    ).exit_code == 0
    
    # Start implementation
    assert runner.invoke(
        app,
        ["--cwd", str(tmp_path), "implement", "start", task_id],
    ).exit_code == 0


class TestTodoImplementationGate:
    """Test suite for todo-based implementation finish gate."""
    
    def test_finish_blocked_by_open_todo(self, tmp_path: Path) -> None:
        """Verify that implement finish is blocked when a todo is open."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add a todo
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "todo", "add",
                "--text", "Implement the main feature.",
            ],
        )
        assert result.exit_code == 0
        
        # Attempt to finish without marking todo done
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        data = _json(result)
        assert data.get("error", {}).get("code") == "IMPLEMENTATION_TODOS_INCOMPLETE"
        assert "open_todos" in data.get("error", {}).get("details", {})
    
    def test_finish_succeeds_when_todos_done(self, tmp_path: Path) -> None:
        """Verify that implement finish succeeds when all todos are done."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add a todo
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "todo", "add",
                "--text", "Implement the main feature.",
            ],
        )
        assert result.exit_code == 0
        todo_data = _json(result)
        todo_id = todo_data["task"]["todos"][0]["id"]
        
        # Mark todo as done
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "todo", "done", todo_id,
            ],
        )
        assert result.exit_code == 0
        
        # Finish implementation should succeed
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code == 0
        data = _json(result)
        assert data.get("ok") is True
        assert data.get("run", {}).get("status") == "finished"
    
    def test_finish_succeeds_with_no_todos(self, tmp_path: Path) -> None:
        """Verify that implement finish succeeds when no todos exist."""
        _prepare_task_for_implementation(tmp_path)
        
        # No todos added - should succeed
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code == 0
        data = _json(result)
        assert data.get("ok") is True
    
    def test_finish_blocked_by_multiple_open_todos(self, tmp_path: Path) -> None:
        """Verify finish is blocked when multiple todos are open."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add multiple todos
        for i in range(3):
            result = runner.invoke(
                app,
                [
                    "--cwd", str(tmp_path),
                    "todo", "add",
                    "--text", f"Todo {i + 1}.",
                ],
            )
            assert result.exit_code == 0
        
        # Mark first todo done
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "todo", "list", "--json"],
        )
        todos = _json(result).get("todos", [])
        first_todo_id = todos[0]["id"]
        
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "todo", "done", first_todo_id],
        )
        assert result.exit_code == 0
        
        # Finish should still be blocked (2 open todos remain)
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        data = _json(result)
        assert data.get("error", {}).get("code") == "IMPLEMENTATION_TODOS_INCOMPLETE"
        open_todos = data.get("error", {}).get("details", {}).get("open_todos", [])
        assert len(open_todos) == 2
    
    def test_finish_succeeds_after_all_todos_done(self, tmp_path: Path) -> None:
        """Verify finish succeeds after marking all todos as done."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add multiple todos
        todo_ids = []
        for i in range(3):
            result = runner.invoke(
                app,
                [
                    "--cwd", str(tmp_path),
                    "todo", "add",
                    "--text", f"Todo {i + 1}.",
                ],
            )
            assert result.exit_code == 0
            task_data = _json(result)
            todo_ids.append(task_data["task"]["todos"][-1]["id"])
        
        # Mark all todos as done
        for todo_id in todo_ids:
            result = runner.invoke(
                app,
                ["--cwd", str(tmp_path), "todo", "done", todo_id],
            )
            assert result.exit_code == 0
        
        # Finish should now succeed
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code == 0
        data = _json(result)
        assert data.get("ok") is True
        assert data.get("run", {}).get("status") == "finished"
    
    def test_lock_remains_active_on_finish_failure(self, tmp_path: Path) -> None:
        """Verify that implementation lock remains active when finish is blocked."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add an open todo
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "todo", "add",
                "--text", "Incomplete todo.",
            ],
        )
        assert result.exit_code == 0
        
        # Attempt to finish
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        
        # Verify lock is still active by checking task status
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "show", "test-task", "--json"],
        )
        assert result.exit_code == 0
        task_data = _json(result)
        # Task should still be in "implementing" stage
        assert task_data.get("task", {}).get("status_stage") == "implementing"
    
    def test_run_remains_running_on_finish_failure(self, tmp_path: Path) -> None:
        """Verify that implementation run remains in 'running' state when finish is blocked."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add an open todo
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "todo", "add",
                "--text", "Incomplete todo.",
            ],
        )
        assert result.exit_code == 0
        
        # Attempt to finish
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        
        # Verify run is still running
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "log", "--json"],
        )
        assert result.exit_code == 0
        run_data = _json(result)
        assert run_data.get("run", {}).get("status") == "running"
    
    def test_error_payload_includes_blockers(self, tmp_path: Path) -> None:
        """Verify error payload includes blocker details."""
        _prepare_task_for_implementation(tmp_path)
        
        # Add multiple todos
        for i in range(2):
            runner.invoke(
                app,
                [
                    "--cwd", str(tmp_path),
                    "todo", "add",
                    "--text", f"Todo {i + 1}.",
                ],
            )
        
        # Attempt to finish
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        data = _json(result)
        
        error_data = data.get("error", {}).get("details", {})
        assert "open_todos" in error_data
        assert len(error_data["open_todos"]) == 2
        assert "blockers" in error_data
        assert len(error_data["blockers"]) == 2
        
        # Each blocker should have kind, ref, message, and command_hint
        for blocker in error_data["blockers"]:
            assert blocker.get("kind") == "todo_open"
            assert blocker.get("ref") is not None
            assert blocker.get("message") is not None
            assert "todo done" in blocker.get("command_hint", "")


class TestTodoBackwardCompatibility:
    """Test suite for backward compatibility with old todo format."""
    
    def test_legacy_done_bool_loads_as_status(self, tmp_path: Path) -> None:
        """Verify that old todos.yaml with only 'done' field loads correctly."""
        _init(tmp_path)
        
        # Create task and manually write legacy todos.yaml
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "task", "create", "legacy-task",
                "--description", "Test legacy todo format.",
            ],
        )
        assert result.exit_code == 0
        
        # Get task to retrieve it
        task_dir = tmp_path / ".taskledger" / "tasks" / "legacy-task"
        todos_file = task_dir / "todos.yaml"
        
        # Write legacy todos.yaml
        legacy_todos = """schema_version: 1
object_type: todos
task_id: legacy-task
todos:
  - id: todo-0001
    text: Legacy done todo
    done: true
    source: user
    mandatory: false
    created_at: "2026-04-24T10:00:00+00:00"
    updated_at: "2026-04-24T10:00:00+00:00"
  - id: todo-0002
    text: Legacy open todo
    done: false
    source: user
    mandatory: false
    created_at: "2026-04-24T10:00:00+00:00"
    updated_at: "2026-04-24T10:00:00+00:00"
"""
        todos_file.write_text(legacy_todos)
        
        # Load task and verify todos are loaded
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "show", "legacy-task", "--json"],
        )
        assert result.exit_code == 0
        task_data = _json(result)
        todos = task_data.get("task", {}).get("todos", [])
        
        # Verify both todos loaded
        assert len(todos) == 2
        assert todos[0]["id"] == "todo-0001"
        assert todos[0]["done"] is True
        assert todos[1]["id"] == "todo-0002"
        assert todos[1]["done"] is False
    
    def test_legacy_todos_dont_block_finish_after_marking_done(self, tmp_path: Path) -> None:
        """Verify legacy todos work with the finish gate after marking done."""
        _prepare_task_for_implementation(tmp_path)
        
        # Manually write legacy todos.yaml
        task_dir = tmp_path / ".taskledger" / "tasks" / "test-task"
        todos_file = task_dir / "todos.yaml"
        
        legacy_todos = """schema_version: 1
object_type: todos
task_id: test-task
todos:
  - id: todo-0001
    text: Legacy todo
    done: false
    source: user
    mandatory: false
    created_at: "2026-04-24T10:00:00+00:00"
    updated_at: "2026-04-24T10:00:00+00:00"
"""
        todos_file.write_text(legacy_todos)
        
        # Attempt to finish - should be blocked
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code != 0
        
        # Mark todo done
        result = runner.invoke(
            app,
            ["--cwd", str(tmp_path), "todo", "done", "todo-0001"],
        )
        assert result.exit_code == 0
        
        # Finish should now succeed
        result = runner.invoke(
            app,
            [
                "--cwd", str(tmp_path),
                "implement", "finish",
                "--summary", "Completed implementation.",
            ],
        )
        assert result.exit_code == 0
