from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.storage.agent_logs import load_agent_command_logs
from taskledger.storage.task_store import resolve_task, resolve_v2_paths


def render_task_transcript(
    workspace_root: Path,
    task_ref: str,
    *,
    format_name: str = "markdown",
    include_output: bool = False,
    limit: int | None = None,
) -> dict[str, object]:
    if format_name not in {"markdown", "json"}:
        raise LaunchError(f"Unsupported transcript format: {format_name}")
    if limit is not None and limit <= 0:
        raise LaunchError("--limit must be a positive integer.")

    task = resolve_task(workspace_root, task_ref)
    logs = load_agent_command_logs(
        workspace_root,
        task_id=task.id,
        limit=limit,
    )

    if format_name == "json":
        return {
            "kind": "task_transcript",
            "task_id": task.id,
            "format": "json",
            "include_output": include_output,
            "limit": limit,
            "logs": [item.to_dict() for item in logs],
        }

    content = _render_markdown(
        workspace_root,
        task_id=task.id,
        logs=logs,
        include_output=include_output,
    )
    return {
        "kind": "task_transcript",
        "task_id": task.id,
        "format": "markdown",
        "include_output": include_output,
        "limit": limit,
        "content": content,
    }


def _render_markdown(
    workspace_root: Path,
    *,
    task_id: str,
    logs: Sequence[object],
    include_output: bool,
) -> str:
    from taskledger.domain.models import AgentCommandLogRecord

    lines: list[str] = ["## Command Transcript", ""]
    lines.append("| Time | Exit | Kind | Command | Output |")
    lines.append("| --- | ---: | --- | --- | --- |")

    typed_logs = [item for item in logs if isinstance(item, AgentCommandLogRecord)]
    if not typed_logs:
        lines.append("| - | - | - | (no command logs) | - |")
        lines.append("")
        return "\n".join(lines) + "\n"

    for item in typed_logs:
        output_refs = _output_ref_summary(item)
        lines.append(
            "| "
            f"{item.started_at} | "
            f"{item.exit_code if item.exit_code is not None else '-'} | "
            f"{item.command_kind} | "
            f"{item.command_line} | "
            f"{output_refs} |"
        )

    lines.append("")

    if include_output:
        paths = resolve_v2_paths(workspace_root)
        for item in typed_logs:
            lines.append(f"### {item.log_id} — {item.command_line}")
            lines.append("")
            exit_value = item.exit_code if item.exit_code is not None else "-"
            lines.append(f"Exit: {exit_value}")
            lines.append(f"Kind: {item.command_kind}")
            if item.run_id:
                lines.append(f"Run: {item.run_id}")
            lines.append("")

            stdout_text = _output_text(
                paths.project_dir,
                item.managed_stdout_ref
                if item.command_kind == "managed_shell"
                else item.visible_stdout_ref,
                item.visible_stdout_excerpt,
            )
            stderr_text = _output_text(
                paths.project_dir,
                item.managed_stderr_ref
                if item.command_kind == "managed_shell"
                else item.visible_stderr_ref,
                item.visible_stderr_excerpt,
            )

            lines.append("#### stdout")
            lines.append("")
            lines.append("```text")
            lines.append(stdout_text if stdout_text else "(empty)")
            lines.append("```")
            lines.append("")

            lines.append("#### stderr")
            lines.append("")
            lines.append("```text")
            lines.append(stderr_text if stderr_text else "(empty)")
            lines.append("```")
            lines.append("")

    return "\n".join(lines) + "\n"


def _output_ref_summary(record: object) -> str:
    from taskledger.domain.models import AgentCommandLogRecord

    if not isinstance(record, AgentCommandLogRecord):
        return "-"
    refs = [
        record.visible_stdout_ref,
        record.visible_stderr_ref,
        record.visible_combined_ref,
        record.managed_stdout_ref,
        record.managed_stderr_ref,
        record.managed_combined_ref,
    ]
    shown = [ref for ref in refs if isinstance(ref, str)]
    if not shown:
        return "inline"
    return ", ".join(shown)


def _output_text(
    project_dir: Path,
    artifact_ref: str | None,
    excerpt: str | None,
) -> str:
    if artifact_ref:
        path = project_dir / artifact_ref
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return excerpt or ""


__all__ = ["render_task_transcript"]
