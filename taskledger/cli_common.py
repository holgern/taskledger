from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from taskledger.errors import LaunchError
from taskledger.models import utc_now_iso


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
                {
                    "success": False,
                    "operation": _operation_name(ctx),
                    "result_type": "error",
                    "data": data or _error_data(error),
                    "warnings": [],
                    "errors": [message],
                    "error": message,
                    "error_type": error_type or _error_type(error),
                    "exit_code": exit_code or _error_exit_code(error),
                    "remediation": remediation or _error_remediation(error),
                    "generated_at": utc_now_iso(),
                }
            )
        )
    else:
        typer.echo(message, err=True)


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
    return {
        "success": True,
        "operation": _operation_name(ctx),
        "result_type": result_type or _infer_result_type(payload),
        "data": payload,
        "warnings": extracted_warnings or [],
        "errors": [],
        "remediation": [],
        "generated_at": utc_now_iso(),
    }


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


def _error_exit_code(error: Exception | str) -> int:
    if isinstance(error, Exception):
        return launch_error_exit_code(error)
    return _exit_code_from_message(str(error), 1)


def _error_type(error: Exception | str) -> str:
    if isinstance(error, Exception):
        explicit = getattr(error, "__dict__", {}).get("taskledger_error_type")
        if isinstance(explicit, str):
            return explicit
        by_exit_code = _error_type_from_exit_code(_error_exit_code(error))
        if by_exit_code:
            return by_exit_code
        return error.__class__.__name__
    by_exit_code = _error_type_from_exit_code(_exit_code_from_message(str(error), 1))
    return by_exit_code or "TaskledgerError"


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


def _exit_code_from_message(message: str, default: int) -> int:
    lowered = message.lower()
    if "not found" in lowered or lowered.startswith("no plans found"):
        return 10
    if "lock already exists" in lowered:
        return 30
    if "invalid yaml" in lowered or "invalid lock file" in lowered:
        return 40
    return default


def _error_type_from_exit_code(exit_code: int) -> str | None:
    return {
        10: "NotFound",
        11: "ValidationError",
        20: "InvalidStageTransition",
        21: "ApprovalRequired",
        22: "DependencyIncomplete",
        30: "LockConflict",
        31: "StaleLockRequiresBreak",
        40: "StorageCorruption",
        41: "IndexRebuildFailed",
    }.get(exit_code)


def _default_remediation(exit_code: int) -> list[str]:
    return {
        10: ["Check the task or record reference and retry."],
        11: ["Review the invalid input or record data and retry."],
        20: ["Move the task through the required staged workflow before retrying."],
        21: ["Approve or revise the plan before retrying the requested operation."],
        22: ["Complete or remove the blocking requirements before retrying."],
        30: ["Inspect the active lock or break it explicitly if it is stale."],
        31: [
            'Break the stale lock explicitly with '
            '`taskledger lock break <task> --reason "..."`.'
        ],
        40: ["Run `taskledger doctor` and repair the ledger state before retrying."],
        41: ["Run `taskledger reindex` and inspect `taskledger doctor` output."],
    }.get(exit_code, [])


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
