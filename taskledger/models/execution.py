from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"
    TERMINATED = "terminated"
    LAUNCH_ERROR = "launch_error"


@dataclass(slots=True, frozen=True)
class TaskledgerExecutionOptions:
    harness_name: str | None
    model_hint: str | None
    config_file: str | None
    live_preview_default: bool | None
    live_output: bool
    render_live: bool
    output_mode: str | None
    output_view: str | None
    primary_config_root: str | None = None
    template_root: str | None = None
    project_config: dict[str, object] | None = None
    extra: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ExecutionCommandInvocation:
    name: str
    raw_line: str
    args: tuple[str, ...]
    source_path: str | None = None


@dataclass(slots=True, frozen=True)
class ExecutionHarnessCapabilities:
    supports_native_completion: bool
    supports_structured_output: bool
    default_structured_output: bool
    supports_final_message_file: bool
    completion_mode: str
    supports_live_events: bool = False
    supports_sessions: bool = False
    structured_output_mode: str = "none"


@dataclass(slots=True, frozen=True)
class ExecutionPreviewRecord:
    harness_name: str | None
    resolved_model: str | None
    command: tuple[str, ...]
    command_display: str | None
    run_cwd: str | None
    final_prompt: str
    prompt_hash: str | None
    prompt_preview: str | None
    original_chars: int
    final_chars: int
    original_prompt: str | None = None
    structured_output: bool = False
    resolved_agent_name: str | None = None
    resolved_variant: str | None = None
    resolved_done_file: str | None = None
    resolved_prompt_template_file: str | None = None
    session_title: str | None = None
    final_message_path: str | None = None
    discovered_config_files: tuple[str, ...] = ()
    primary_config_root: str | None = None
    value_sources: dict[str, dict[str, str | None]] | None = None
    harness_config_env: dict[str, str] | None = None
    provider_env: dict[str, str] | None = None
    env_keys_applied: list[str] | None = None
    provider_settings: dict[str, object] | None = None
    provider_metadata: dict[str, object] | None = None
    templated: bool = False
    done_file_suffix_injected: bool = False
    prompt_after_template: str | None = None
    prompt_after_command_expansion: str | None = None
    expanded_commands: tuple[ExecutionCommandInvocation, ...] = ()
    read_roots: tuple[str, ...] = ()
    write_roots: tuple[str, ...] = ()
    harness_capabilities: ExecutionHarnessCapabilities | None = None
    metadata: dict[str, object] | None = None

    @property
    def summary_line(self) -> str:
        descriptor = (
            self.harness_name
            if not self.resolved_model
            else f"{self.harness_name}/{self.resolved_model}"
        )
        return f"PREVIEW  {descriptor}"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        payload["discovered_config_files"] = list(self.discovered_config_files)
        return payload

    def to_json(self, *, indent: int | None = None, sort_keys: bool = False) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)



@dataclass(slots=True, frozen=True)
class ExecutionOutcomeRecord:
    harness: str | None
    status: ExecutionStatus
    prompt: str
    cwd: str | None
    command: tuple[str, ...]
    returncode: int | None
    pid: int | None
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    completion_method: str | None
    stdout: str | None
    stderr: str | None
    done_file: str | None
    final_message: str | None = None
    session_id: str | None = None
    session_title: str | None = None
    provider_metadata: dict[str, object] | None = None
    terminal_event: dict[str, object] | None = None
    event_count: int | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    runtime_warnings: list[str] | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    capture_strategy: str | None = None
    structured_output: bool = False
    resolved_model: str | None = None
    resolved_agent_name: str | None = None
    resolved_variant: str | None = None
    resolved_prompt_template_file: str | None = None
    resolved_config_files: tuple[str, ...] = ()
    resolved_primary_config_root: str | None = None
    resolved_value_sources: dict[str, dict[str, str | None]] | None = None
    prompt_hash: str | None = None
    prompt_preview: str | None = None
    prompt_token_estimate: int | None = None
    output_preview: str | None = None
    output_token_estimate: int | None = None
    total_token_estimate: int | None = None
    prompt_after_template: str | None = None
    prompt_after_command_expansion: str | None = None
    command_display: str | None = None
    env_keys_applied: list[str] | None = None
    final_message_path_used: bool = False
    stdout_transcript_path: str | None = None
    stderr_transcript_path: str | None = None
    event_transcript_path: str | None = None
    read_roots: tuple[str, ...] = ()
    write_roots: tuple[str, ...] = ()
    metadata: dict[str, object] | None = None

    @property
    def ok(self) -> bool:
        return self.status == ExecutionStatus.SUCCEEDED

    @property
    def best_text(self) -> str | None:
        if self.final_message:
            return self.final_message
        if self.stdout:
            return self.stdout
        if self.stderr:
            lines = [line for line in self.stderr.splitlines() if line.strip()]
            if lines:
                return "\n".join(lines[-3:])
        return None

    @property
    def summary_line(self) -> str:
        completion_method = self.completion_method or "unknown"
        harness = self.harness or "unknown"
        return (
            f"{harness}  {self.status.value}  "
            f"{self.duration_seconds:.1f}s  via {completion_method}"
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["command"] = list(self.command)
        payload["started_at"] = self.started_at.isoformat()
        payload["finished_at"] = self.finished_at.isoformat()
        payload["resolved_config_files"] = list(self.resolved_config_files)
        payload["read_roots"] = list(self.read_roots)
        payload["write_roots"] = list(self.write_roots)
        return payload

    def to_json(self, *, indent: int | None = None, sort_keys: bool = False) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)
