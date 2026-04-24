from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from taskledger.errors import LaunchError, TaskledgerError
from taskledger.storage.v2 import TaskRecord, resolve_task_or_active


@dataclass(slots=True, frozen=True)
class CLIState:
    cwd: Path
    json_output: bool


def resolve_workspace_root(cwd: Path | None) -> Path:
    return (cwd or Path.cwd()).expanduser().resolve()


def cli_state_from_context(ctx: typer.Context) -> CLIState:
    state = ctx.obj
    if not isinstance(state, CLIState):
        raise LaunchError("Taskledger CLI state is not initialized.")
    return state


def resolve_cli_task(workspace_root: Path, task_ref: str | None) -> TaskRecord:
    return resolve_task_or_active(workspace_root, task_ref)


def render_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def emit_payload(
    ctx: typer.Context,
    payload: Any,
    *,
    human: str | None = None,
    result_type: str | None = None,
    warnings: list[str] | None = None,
) -> None:
    state = cli_state_from_context(ctx)
    if state.json_output:
        typer.echo(
            render_json(
                _success_envelope(
                    ctx,
                    payload,
                    result_type=result_type,
                    warnings=warnings,
                )
            )
        )
        return
    if human is None:
        if isinstance(payload, dict):
            human = "\n".join(
                f"{key}: {value}" for key, value in payload.items() if value is not None
            )
        else:
            human = str(payload)
    typer.echo(human)


def emit_error(
    ctx: typer.Context,
    error: Exception | str,
    *,
    data: dict[str, object] | None = None,
    remediation: list[str] | None = None,
    exit_code: int | None = None,
    error_type: str | None = None,
) -> None:
    state = cli_state_from_context(ctx)
    message = str(error)
    if state.json_output:
        typer.echo(
            render_json(
                _error_envelope(
                    ctx,
                    error,
                    data=data,
                    remediation=remediation,
                    exit_code=exit_code,
                    error_type=error_type,
                )
            )
        )
    else:
        human_output = _format_human_error(error)
        typer.echo(human_output, err=True)


def launch_error_exit_code(exc: Exception, default: int = 1) -> int:
    code = getattr(exc, "taskledger_exit_code", None)
    if not isinstance(code, int):
        code = getattr(exc, "exit_code", None)
    if not isinstance(code, int):
        code = _exit_code_from_message(str(exc), default)
    return code if isinstance(code, int) else default


def _success_envelope(
    ctx: typer.Context,
    payload: Any,
    *,
    result_type: str | None,
    warnings: list[str] | None,
) -> dict[str, object]:
    extracted_warnings = warnings
    if extracted_warnings is None and isinstance(payload, dict):
        raw_warnings = payload.get("warnings")
        if isinstance(raw_warnings, list):
            extracted_warnings = [str(item) for item in raw_warnings]
    envelope: dict[str, object] = {
        "ok": True,
        "command": _operation_name(ctx),
        "result": payload,
        "events": _event_refs(payload),
    }
    task_id = _task_id_from_value(payload)
    if task_id is not None:
        envelope["task_id"] = task_id
    if extracted_warnings:
        envelope["warnings"] = extracted_warnings
    if result_type is not None:
        envelope["result_type"] = result_type
    return envelope


def _operation_name(ctx: typer.Context) -> str:
    root_name = ctx.find_root().info_name
    parts = ctx.command_path.split()
    if root_name and parts and parts[0] == root_name:
        parts = parts[1:]
    return ".".join(parts) if parts else "taskledger"


def _infer_result_type(payload: Any) -> str:
    if isinstance(payload, list):
        return "collection"
    if isinstance(payload, str):
        return "text"
    if not isinstance(payload, dict):
        return type(payload).__name__
    if isinstance(payload.get("task"), dict):
        return "task"
    if isinstance(payload.get("plan"), dict):
        return "plan"
    if isinstance(payload.get("run"), dict):
        return "run"
    if isinstance(payload.get("todo"), dict):
        return "todo"
    if "lock" in payload:
        return "lock"
    if {"id", "status_stage", "title"}.issubset(payload):
        return "task"
    if {"run_id", "run_type", "status"}.issubset(payload):
        return "run"
    if {"task_id", "plan_version", "status"}.issubset(payload):
        return "plan"
    if any(
        key in payload
        for key in ("tasks", "plans", "questions", "locks", "file_links")
    ):
        return "collection"
    kind = payload.get("kind")
    return str(kind) if kind else "object"


def _error_envelope(
    ctx: typer.Context,
    error: Exception | str,
    *,
    data: dict[str, object] | None,
    remediation: list[str] | None,
    exit_code: int | None,
    error_type: str | None,
) -> dict[str, object]:
    resolved_error = _error_payload(
        error,
        data=data,
        remediation=remediation,
        exit_code=exit_code,
        error_type=error_type,
    )
    envelope: dict[str, object] = {
        "ok": False,
        "command": _operation_name(ctx),
        "error": resolved_error,
    }
    task_id = resolved_error.get("task_id")
    if isinstance(task_id, str):
        envelope["task_id"] = task_id
    return envelope


def _error_exit_code(error: Exception | str) -> int:
    if isinstance(error, Exception):
        return launch_error_exit_code(error)
    return _exit_code_from_message(str(error), 1)


def _error_data(error: Exception | str) -> dict[str, object]:
    if isinstance(error, Exception):
        payload = getattr(error, "taskledger_data", None)
        if isinstance(payload, dict):
            return dict(payload)
    return {}


def _error_remediation(error: Exception | str) -> list[str]:
    if isinstance(error, Exception):
        explicit = getattr(error, "taskledger_remediation", None)
        if isinstance(explicit, list) and explicit:
            return [str(item) for item in explicit]
    return _default_remediation(_error_exit_code(error))


def _error_payload(
    error: Exception | str,
    *,
    data: dict[str, object] | None,
    remediation: list[str] | None,
    exit_code: int | None,
    error_type: str | None,
) -> dict[str, object]:
    if isinstance(error, TaskledgerError):
        payload = error.to_error_payload()
    else:
        payload = {
            "code": _error_code(error, explicit_error_type=error_type, explicit_exit_code=exit_code),
            "message": str(error),
        }
    payload["code"] = _error_code(
        error,
        explicit_error_type=error_type,
        explicit_exit_code=exit_code,
    )
    details = data or _error_details(error)
    if details:
        existing = payload.get("details")
        merged = dict(existing) if isinstance(existing, dict) else {}
        merged.update(details)
        payload["details"] = merged
    blocking_refs = _error_blocking_refs(error)
    if blocking_refs:
        payload["blocking_refs"] = blocking_refs
    task_id = _error_task_id(error)
    if task_id is not None:
        payload["task_id"] = task_id
    resolved_remediation = remediation or _error_remediation(error)
    if resolved_remediation:
        payload["remediation"] = resolved_remediation
    resolved_exit_code = exit_code or _error_exit_code(error)
    if resolved_exit_code:
        payload["exit_code"] = resolved_exit_code
    return payload


def _error_code(
    error: Exception | str,
    *,
    explicit_error_type: str | None = None,
    explicit_exit_code: int | None = None,
) -> str:
    if isinstance(error, TaskledgerError):
        explicit = getattr(error, "__dict__", {}).get("taskledger_error_code")
        if isinstance(explicit, str) and explicit not in {"TASKLEDGER_ERROR", "LAUNCH_ERROR"}:
            return explicit
        legacy_type = explicit_error_type or getattr(error, "__dict__", {}).get(
            "taskledger_error_type"
        )
        if isinstance(legacy_type, str):
            mapped = _error_code_from_error_type(legacy_type)
            if mapped is not None and error.code in {"TASKLEDGER_ERROR", "LAUNCH_ERROR"}:
                return mapped
        by_exit_code = _error_code_from_exit_code(
            explicit_exit_code if explicit_exit_code is not None else _error_exit_code(error)
        )
        if by_exit_code is not None and error.code in {"TASKLEDGER_ERROR", "LAUNCH_ERROR"}:
            return by_exit_code
        return error.code
    if isinstance(error, Exception):
        explicit = getattr(error, "__dict__", {}).get("taskledger_error_code")
        if isinstance(explicit, str):
            return explicit
        legacy_type = explicit_error_type or getattr(error, "__dict__", {}).get(
            "taskledger_error_type"
        )
        if isinstance(legacy_type, str):
            mapped = _error_code_from_error_type(legacy_type)
            if mapped is not None:
                return mapped
    by_exit_code = _error_code_from_exit_code(
        explicit_exit_code if explicit_exit_code is not None else _error_exit_code(error)
    )
    if by_exit_code is not None:
        return by_exit_code
    return "TASKLEDGER_ERROR"


def _error_details(error: Exception | str) -> dict[str, object]:
    payload = _error_data(error)
    return {
        key: value
        for key, value in payload.items()
        if key not in {"code", "message", "task_id", "blocking_refs"}
    }


def _error_task_id(error: Exception | str) -> str | None:
    if isinstance(error, TaskledgerError) and error.task_id is not None:
        return error.task_id
    payload = _error_data(error)
    task_id = payload.get("task_id")
    if isinstance(task_id, str):
        return task_id
    return None


def _error_blocking_refs(error: Exception | str) -> list[str]:
    if isinstance(error, TaskledgerError) and error.blocking_refs:
        return [str(item) for item in error.blocking_refs]
    payload = _error_data(error)
    blocking_refs = payload.get("blocking_refs")
    if isinstance(blocking_refs, list):
        return [str(item) for item in blocking_refs]
    return []


def _exit_code_from_message(message: str, default: int) -> int:
    lowered = message.lower()
    if "not found" in lowered or lowered.startswith("no plans found"):
        return 5
    if "lock already exists" in lowered:
        return 4
    if "invalid yaml" in lowered or "invalid lock file" in lowered:
        return 6
    return default


def _error_code_from_error_type(error_type: str) -> str | None:
    return {
        "ApprovalRequired": "APPROVAL_REQUIRED",
        "DependencyIncomplete": "DEPENDENCY_INCOMPLETE",
        "InvalidStageTransition": "INVALID_STAGE_TRANSITION",
        "LockConflict": "LOCK_CONFLICT",
        "NotFound": "NOT_FOUND",
        "StaleLockRequiresBreak": "STALE_LOCK_REQUIRES_BREAK",
        "StorageCorruption": "STORAGE_CORRUPTION",
        "ValidationError": "VALIDATION_FAILED",
    }.get(error_type)


def _error_code_from_exit_code(exit_code: int) -> str | None:
    return {
        2: "INVALID_INPUT",
        3: "WORKFLOW_REJECTION",
        4: "LOCK_CONFLICT",
        5: "NOT_FOUND",
        6: "STORAGE_ERROR",
        7: "VALIDATION_FAILED",
    }.get(exit_code)


def _default_remediation(exit_code: int) -> list[str]:
    return {
        2: ["Review the invalid input or command usage and retry."],
        3: ["Move the task through the required workflow gate before retrying."],
        4: ["Inspect the active lock or break it explicitly if it is stale."],
        5: ["Check the task or record reference and retry."],
        6: ["Run `taskledger doctor` and repair the ledger state before retrying."],
        7: ["Review the recorded validation results and resolve the failing checks."],
    }.get(exit_code, [])


def _format_human_error(error: Exception | str) -> str:
    """Format error for human-readable output with special handling for validation errors."""
    message = str(error)
    error_code = None
    error_data = {}
    
    if isinstance(error, Exception):
        error_code = getattr(error, "taskledger_error_code", None)
        payload = getattr(error, "taskledger_data", None)
        if isinstance(payload, dict):
            error_data = payload
    
    if error_code == "VALIDATION_INCOMPLETE":
        lines = [f"Error: {message}", ""]
        
        missing_criteria = error_data.get("missing_criteria", [])
        if missing_criteria and isinstance(missing_criteria, list):
            lines.append("Missing Mandatory Criteria:")
            for criterion in missing_criteria:
                lines.append(f"  • {criterion}")
            lines.append("")
        
        failing_criteria = error_data.get("failing_criteria", [])
        if failing_criteria and isinstance(failing_criteria, list):
            lines.append("Failing Mandatory Criteria:")
            for criterion in failing_criteria:
                lines.append(f"  ✗ {criterion}")
            lines.append("")
        
        open_mandatory_todos = error_data.get("open_mandatory_todos", [])
        if open_mandatory_todos and isinstance(open_mandatory_todos, list):
            lines.append("Open Mandatory Todos:")
            for todo_id in open_mandatory_todos:
                lines.append(f"  ☐ {todo_id}")
            lines.append("")
        
        dependency_blockers = error_data.get("dependency_blockers", [])
        if dependency_blockers and isinstance(dependency_blockers, list):
            lines.append("Dependency Blockers:")
            for blocker in dependency_blockers:
                lines.append(f"  - {blocker}")
            lines.append("")
        
        blockers = error_data.get("blockers", [])
        if blockers and isinstance(blockers, list):
            lines.append("Blocking Issues:")
            for blocker in blockers:
                if isinstance(blocker, dict):
                    kind = blocker.get("kind", "unknown")
                    msg = blocker.get("message", "")
                    hint = blocker.get("command_hint", "")
                    lines.append(f"  [{kind}] {msg}")
                    if hint:
                        lines.append(f"    Command: {hint}")
            lines.append("")
        
        lines.append("Next Steps:")
        lines.append("  1. Review the blocking issues above")
        lines.append("  2. Address the validation gates")
        lines.append("  3. Run 'taskledger validate status' to check progress")
        
        return "\n".join(lines)
    
    return message


def _task_id_from_value(value: Any) -> str | None:
    if isinstance(value, dict):
        direct = value.get("task_id")
        if isinstance(direct, str):
            return direct
        candidate = value.get("id")
        if isinstance(candidate, str) and candidate.startswith("task-"):
            return candidate
        nested_task = value.get("task")
        if isinstance(nested_task, dict):
            nested_id = nested_task.get("id")
            if isinstance(nested_id, str):
                return nested_id
    return None


def _event_refs(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    events = payload.get("events")
    if isinstance(events, list):
        return [str(item) for item in events]
    return []


def read_text_input(
    *,
    text: str | None,
    from_file: Path | None = None,
    text_label: str = "--text",
) -> str:
    if text and from_file is not None:
        raise LaunchError(f"Use either {text_label} or --from-file, not both.")
    if from_file is not None:
        try:
            return from_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise LaunchError(f"Failed to read {from_file}: {exc}") from exc
    if text is None:
        raise LaunchError(f"Provide {text_label} or --from-file.")
    if not text.strip():
        raise LaunchError("Text input must not be empty.")
    return text


def write_text_output(path: Path, text: str) -> Path:
    target = path.expanduser()
    parent = target.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise LaunchError(f"Failed to write {target}: {exc}") from exc
    return target


def human_kv(title: str, rows: list[tuple[str, object]]) -> str:
    lines = [title]
    for key, value in rows:
        if value is None:
            continue
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def human_list(title: str, rows: list[str]) -> str:
    if not rows:
        return f"{title}\n(empty)"
    return "\n".join([title, *rows])
