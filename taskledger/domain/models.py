from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from taskledger.domain.states import (
    TASKLEDGER_SCHEMA_VERSION,
    TASKLEDGER_V2_FILE_VERSION,
    ActiveTaskStatusStage,
    FileLinkKind,
    PlanStatus,
    QuestionStatus,
    RunStatus,
    RunType,
    TaskStatusStage,
    ValidationCheckStatus,
    ValidationResult,
    normalize_actor_role,
    normalize_actor_type,
    normalize_file_link_kind,
    normalize_handoff_mode,
    normalize_handoff_status,
    normalize_harness_kind,
    normalize_lock_policy,
    normalize_plan_status,
    normalize_question_status,
    normalize_run_status,
    normalize_run_type,
    normalize_task_status_stage,
    normalize_validation_check_status,
    normalize_validation_result,
)
from taskledger.errors import LaunchError
from taskledger.timeutils import utc_now_iso


@dataclass(slots=True, frozen=True)
class ActorRef:
    actor_type: Literal["agent", "user", "system"] = "agent"
    actor_name: str = "taskledger"
    tool: str | None = None
    session_id: str | None = None
    host: str | None = None
    pid: int | None = None
    actor_id: str | None = None
    role: (
        Literal["planner", "implementer", "validator", "reviewer", "operator"] | None
    ) = None
    harness_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "tool": self.tool,
            "session_id": self.session_id,
            "host": self.host,
            "pid": self.pid,
            "actor_id": self.actor_id,
            "role": self.role,
            "harness_id": self.harness_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> ActorRef:
        if not isinstance(data, dict):
            return cls()
        raw_actor_type = _optional_string(data.get("actor_type")) or "agent"
        actor_type = normalize_actor_type(raw_actor_type)
        pid = data.get("pid")
        raw_role = _optional_string(data.get("role"))
        role = normalize_actor_role(raw_role) if raw_role else None
        return cls(
            actor_type=actor_type,
            actor_name=_optional_string(data.get("actor_name")) or "taskledger",
            tool=_optional_string(data.get("tool")),
            session_id=_optional_string(data.get("session_id")),
            host=_optional_string(data.get("host")),
            pid=pid if isinstance(pid, int) else None,
            actor_id=_optional_string(data.get("actor_id")),
            role=role,
            harness_id=_optional_string(data.get("harness_id")),
        )


@dataclass(slots=True, frozen=True)
class HarnessRef:
    harness_id: str
    name: str
    kind: Literal["agent_harness", "manual", "ci", "unknown"] = "unknown"
    session_id: str | None = None
    working_directory: str | None = None
    command: str | None = None
    version: str | None = None
    capabilities: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now_iso)
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "harness"

    def to_dict(self) -> dict[str, object]:
        return {
            "harness_id": self.harness_id,
            "name": self.name,
            "kind": self.kind,
            "session_id": self.session_id,
            "working_directory": self.working_directory,
            "command": self.command,
            "version": self.version,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "object_type": self.object_type,
        }

    @classmethod
    def from_dict(cls, data: object) -> HarnessRef:
        if not isinstance(data, dict):
            raise LaunchError("Invalid harness data: expected mapping")
        _require_contract(data, expected_object_type="harness")
        return cls(
            harness_id=_string_value(data, "harness_id"),
            name=_string_value(data, "name"),
            kind=normalize_harness_kind(
                _optional_string(data.get("kind")) or "unknown"
            ),
            session_id=_optional_string(data.get("session_id")),
            working_directory=_optional_string(data.get("working_directory")),
            command=_optional_string(data.get("command")),
            version=_optional_string(data.get("version")),
            capabilities=tuple(_optional_list_string(data.get("capabilities")) or []),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            schema_version=_int_value(data, "schema_version"),
        )


@dataclass(slots=True, frozen=True)
class TaskHandoffRecord:
    handoff_id: str
    task_id: str
    mode: Literal["planning", "implementation", "validation", "review", "full"]

    status: Literal["open", "claimed", "closed", "cancelled"] = field(default="open")
    lock_policy: Literal["none", "retain", "release", "transfer"] = field(
        default="none"
    )
    context_body: str = field(default="")
    file_version: str = field(default=TASKLEDGER_V2_FILE_VERSION)
    schema_version: int = field(default=TASKLEDGER_SCHEMA_VERSION)
    object_type: str = field(default="handoff")

    created_from_harness: HarnessRef | None = field(default=None)
    intended_actor_type: Literal["agent", "user", "system"] | None = field(default=None)
    intended_actor_name: str | None = field(default=None)
    intended_harness: str | None = field(default=None)
    source_run_id: str | None = field(default=None)
    resumes_run_id: str | None = field(default=None)
    claim_run_id: str | None = field(default=None)
    released_lock_id: str | None = field(default=None)
    claimed_at: str | None = field(default=None)
    claimed_by: ActorRef | None = field(default=None)
    claimed_in_harness: HarnessRef | None = field(default=None)
    summary: str | None = field(default=None)
    next_action: str | None = field(default=None)

    created_at: str = field(default_factory=utc_now_iso)
    created_by: ActorRef = field(default_factory=ActorRef)

    def to_dict(self) -> dict[str, object]:
        return {
            "handoff_id": self.handoff_id,
            "task_id": self.task_id,
            "mode": self.mode,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by.to_dict(),
            "created_from_harness": self.created_from_harness.to_dict()
            if self.created_from_harness
            else None,
            "intended_actor_type": self.intended_actor_type,
            "intended_actor_name": self.intended_actor_name,
            "intended_harness": self.intended_harness,
            "source_run_id": self.source_run_id,
            "resumes_run_id": self.resumes_run_id,
            "claim_run_id": self.claim_run_id,
            "lock_policy": self.lock_policy,
            "released_lock_id": self.released_lock_id,
            "claimed_at": self.claimed_at,
            "claimed_by": self.claimed_by.to_dict() if self.claimed_by else None,
            "claimed_in_harness": self.claimed_in_harness.to_dict()
            if self.claimed_in_harness
            else None,
            "summary": self.summary,
            "next_action": self.next_action,
            "context_body": self.context_body,
            "file_version": self.file_version,
            "schema_version": self.schema_version,
            "object_type": self.object_type,
        }

    @classmethod
    def from_dict(cls, data: object) -> TaskHandoffRecord:
        if not isinstance(data, dict):
            raise LaunchError("Invalid handoff record: expected mapping")
        _require_contract(data, expected_object_type="handoff")
        return cls(
            handoff_id=_string_value(data, "handoff_id"),
            task_id=_string_value(data, "task_id"),
            mode=normalize_handoff_mode(_string_value(data, "mode")),
            status=normalize_handoff_status(
                _optional_string(data.get("status")) or "open"
            ),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            created_by=ActorRef.from_dict(data.get("created_by")),
            created_from_harness=HarnessRef.from_dict(data.get("created_from_harness"))
            if data.get("created_from_harness")
            else None,
            intended_actor_type=(
                normalize_actor_type(v)
                if (v := _optional_string(data.get("intended_actor_type")))
                else None
            ),
            intended_actor_name=_optional_string(data.get("intended_actor_name")),
            intended_harness=_optional_string(data.get("intended_harness")),
            source_run_id=_optional_string(data.get("source_run_id")),
            resumes_run_id=_optional_string(data.get("resumes_run_id")),
            claim_run_id=_optional_string(data.get("claim_run_id")),
            lock_policy=normalize_lock_policy(
                _optional_string(data.get("lock_policy")) or "none"
            ),
            released_lock_id=_optional_string(data.get("released_lock_id")),
            claimed_at=_optional_string(data.get("claimed_at")),
            claimed_by=ActorRef.from_dict(data.get("claimed_by"))
            if data.get("claimed_by")
            else None,
            claimed_in_harness=HarnessRef.from_dict(data.get("claimed_in_harness"))
            if data.get("claimed_in_harness")
            else None,
            summary=_optional_string(data.get("summary")),
            next_action=_optional_string(data.get("next_action")),
            context_body=_optional_string(data.get("context_body")) or "",
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
        )


@dataclass(slots=True, frozen=True)
class ActiveTaskState:
    task_id: str
    activated_at: str = field(default_factory=utc_now_iso)
    activated_by: ActorRef = field(default_factory=ActorRef)
    reason: str | None = None
    previous_task_id: str | None = None
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "active_task"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "task_id": self.task_id,
            "activated_at": self.activated_at,
            "activated_by": self.activated_by.to_dict(),
            "reason": self.reason,
            "previous_task_id": self.previous_task_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> ActiveTaskState:
        if not isinstance(data, dict):
            raise LaunchError("Invalid active task state: expected mapping.")
        _require_contract(data, expected_object_type="active_task")
        return cls(
            task_id=_string_value(data, "task_id"),
            activated_at=_optional_string(data.get("activated_at")) or utc_now_iso(),
            activated_by=ActorRef.from_dict(data.get("activated_by")),
            reason=_optional_string(data.get("reason")),
            previous_task_id=_optional_string(data.get("previous_task_id")),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class ActiveActorState:
    actor_type: Literal["agent", "user", "system"] = "agent"
    actor_name: str = "taskledger"
    role: (
        Literal["planner", "implementer", "validator", "reviewer", "operator"] | None
    ) = None
    tool: str | None = None
    session_id: str | None = None
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "active_actor"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "role": self.role,
            "tool": self.tool,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> ActiveActorState:
        if not isinstance(data, dict):
            raise LaunchError("Invalid active actor state: expected mapping.")
        _require_contract(data, expected_object_type="active_actor")
        raw_role = _optional_string(data.get("role"))
        return cls(
            actor_type=normalize_actor_type(
                _optional_string(data.get("actor_type")) or "agent"
            ),
            actor_name=_optional_string(data.get("actor_name")) or "taskledger",
            role=normalize_actor_role(raw_role) if raw_role else None,
            tool=_optional_string(data.get("tool")),
            session_id=_optional_string(data.get("session_id")),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class ActiveHarnessState:
    name: str = "unknown"
    kind: Literal["agent_harness", "manual", "ci", "unknown"] = "unknown"
    session_id: str | None = None
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "active_harness"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "name": self.name,
            "kind": self.kind,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> ActiveHarnessState:
        if not isinstance(data, dict):
            raise LaunchError("Invalid active harness state: expected mapping.")
        _require_contract(data, expected_object_type="active_harness")
        raw_kind = _optional_string(data.get("kind"))
        return cls(
            name=_optional_string(data.get("name")) or "unknown",
            kind=normalize_harness_kind(raw_kind) if raw_kind else "unknown",
            session_id=_optional_string(data.get("session_id")),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class FileLink:
    path: str
    kind: FileLinkKind = "code"
    label: str | None = None
    required_for_validation: bool = False
    id: str | None = None
    task_id: str | None = None
    target_type: str | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "link"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "path": self.path,
            "kind": self.kind,
            "label": self.label,
            "required_for_validation": self.required_for_validation,
            "target_type": self.target_type,
            "file_version": self.file_version,
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> FileLink:
        if not isinstance(data, dict):
            raise LaunchError("Invalid file link: expected mapping.")
        return cls(
            id=_optional_string(data.get("id")),
            task_id=_optional_string(data.get("task_id")),
            path=_string_value(data, "path"),
            kind=normalize_file_link_kind(_optional_string(data.get("kind")) or "code"),
            label=_optional_string(data.get("label")),
            required_for_validation=bool(data.get("required_for_validation", False)),
            target_type=_optional_string(data.get("target_type")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_or_default(
                data.get("schema_version"), TASKLEDGER_SCHEMA_VERSION
            ),
            object_type=_optional_string(data.get("object_type")) or "link",
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
        )


@dataclass(slots=True, frozen=True)
class TaskTodo:
    id: str
    text: str
    done: bool = False
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    source: str | None = None
    mandatory: bool = False
    # Extended fields for richer todo tracking
    status: str = "open"  # Will be validated to TodoStatus
    active_at: str | None = None
    blocked_reason: str | None = None
    done_at: str | None = None
    skipped_at: str | None = None
    completed_by: ActorRef | None = None
    completed_in_harness: HarnessRef | None = None
    skipped_by: ActorRef | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    change_refs: tuple[str, ...] = field(default_factory=tuple)
    command_refs: tuple[str, ...] = field(default_factory=tuple)
    source_plan_id: str | None = None
    source_question_ids: tuple[str, ...] = field(default_factory=tuple)
    validation_hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "mandatory": self.mandatory,
            "status": self.status,
            "active_at": self.active_at,
            "blocked_reason": self.blocked_reason,
            "done_at": self.done_at,
            "skipped_at": self.skipped_at,
            "completed_by": self.completed_by.to_dict() if self.completed_by else None,
            "completed_in_harness": (
                self.completed_in_harness.to_dict()
                if self.completed_in_harness
                else None
            ),
            "skipped_by": self.skipped_by.to_dict() if self.skipped_by else None,
            "evidence": list(self.evidence),
            "artifact_refs": list(self.artifact_refs),
            "change_refs": self.change_refs,
            "command_refs": self.command_refs,
            "source_plan_id": self.source_plan_id,
            "source_question_ids": list(self.source_question_ids),
            "validation_hint": self.validation_hint,
        }

    @classmethod
    def from_dict(cls, data: object) -> TaskTodo:
        if not isinstance(data, dict):
            raise LaunchError("Invalid todo: expected mapping.")

        # Handle backward compatibility: infer status from done field if not present
        status_raw = _optional_string(data.get("status"))
        if status_raw is None:
            status = "done" if bool(data.get("done", False)) else "open"
        else:
            from taskledger.domain.states import normalize_todo_status

            status = normalize_todo_status(status_raw)

        # Parse completed_by and skipped_by
        completed_by_data = data.get("completed_by")
        completed_by = (
            ActorRef.from_dict(completed_by_data) if completed_by_data else None
        )
        completed_in_harness_data = data.get("completed_in_harness")
        completed_in_harness = (
            HarnessRef.from_dict(completed_in_harness_data)
            if completed_in_harness_data
            else None
        )
        skipped_by_data = data.get("skipped_by")
        skipped_by = ActorRef.from_dict(skipped_by_data) if skipped_by_data else None

        # Parse evidence and refs
        evidence = _string_tuple(data.get("evidence"))
        artifact_refs = _string_tuple(data.get("artifact_refs")) or _string_tuple(
            data.get("artifacts")
        )
        change_refs = _string_tuple(data.get("change_refs")) or _string_tuple(
            data.get("changes")
        )
        command_refs = _string_tuple(data.get("command_refs"))

        return cls(
            id=_string_value(data, "id"),
            text=_string_value(data, "text"),
            done=bool(data.get("done", False)),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            source=_optional_string(data.get("source")),
            mandatory=bool(data.get("mandatory", False)),
            status=status,
            active_at=_optional_string(data.get("active_at")),
            blocked_reason=_optional_string(data.get("blocked_reason")),
            done_at=_optional_string(data.get("done_at")),
            skipped_at=_optional_string(data.get("skipped_at")),
            completed_by=completed_by,
            completed_in_harness=completed_in_harness,
            skipped_by=skipped_by,
            evidence=evidence,
            artifact_refs=artifact_refs,
            change_refs=change_refs,
            command_refs=command_refs,
            source_plan_id=_optional_string(data.get("source_plan_id")),
            source_question_ids=_string_tuple(data.get("source_question_ids")),
            validation_hint=_optional_string(data.get("validation_hint")),
        )


@dataclass(slots=True, frozen=True)
class AcceptanceCriterion:
    id: str
    text: str
    mandatory: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "mandatory": self.mandatory,
        }

    @classmethod
    def from_dict(cls, data: object) -> AcceptanceCriterion:
        if not isinstance(data, dict):
            raise LaunchError("Invalid acceptance criterion: expected mapping.")
        return cls(
            id=_string_value(data, "id"),
            text=_string_value(data, "text"),
            mandatory=bool(data.get("mandatory", True)),
        )


@dataclass(slots=True, frozen=True)
class CriterionWaiver:
    actor: ActorRef = field(default_factory=ActorRef)
    reason: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor.to_dict(),
            "reason": self.reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> CriterionWaiver | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise LaunchError("Invalid criterion waiver: expected mapping.")
        return cls(
            actor=ActorRef.from_dict(data.get("actor")),
            reason=_string_value(data, "reason"),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
        )


@dataclass(slots=True, frozen=True)
class DependencyWaiver:
    actor: ActorRef = field(default_factory=ActorRef)
    reason: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor.to_dict(),
            "reason": self.reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> DependencyWaiver | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise LaunchError("Invalid dependency waiver: expected mapping.")
        return cls(
            actor=ActorRef.from_dict(data.get("actor")),
            reason=_string_value(data, "reason"),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
        )


@dataclass(slots=True, frozen=True)
class DependencyRequirement:
    task_id: str
    required_status: str = "done"
    waiver: DependencyWaiver | None = None
    id: str | None = None
    required_task_id: str | None = None
    parent_task_id: str | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "requirement"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "task_id": self.required_task_id or self.task_id,
            "required_task_id": self.required_task_id or self.task_id,
            "parent_task_id": self.parent_task_id,
            "required_status": self.required_status,
            "waiver": self.waiver.to_dict() if self.waiver is not None else None,
            "file_version": self.file_version,
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> DependencyRequirement:
        if not isinstance(data, dict):
            raise LaunchError("Invalid dependency requirement: expected mapping.")
        task_id = _optional_string(data.get("required_task_id")) or _string_value(
            data, "task_id"
        )
        return cls(
            id=_optional_string(data.get("id")),
            task_id=task_id,
            required_task_id=_optional_string(data.get("required_task_id")) or task_id,
            parent_task_id=_optional_string(data.get("parent_task_id")),
            required_status=_optional_string(data.get("required_status")) or "done",
            waiver=DependencyWaiver.from_dict(data.get("waiver")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_or_default(
                data.get("schema_version"), TASKLEDGER_SCHEMA_VERSION
            ),
            object_type=_optional_string(data.get("object_type")) or "requirement",
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
        )


@dataclass(slots=True, frozen=True)
class ValidationCheck:
    name: str
    id: str | None = None
    criterion_id: str | None = None
    status: ValidationCheckStatus = "pass"
    details: str | None = None
    evidence: tuple[str, ...] = ()
    waiver: CriterionWaiver | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "criterion_id": self.criterion_id,
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "evidence": list(self.evidence),
            "waiver": self.waiver.to_dict() if self.waiver is not None else None,
        }
        return payload

    @classmethod
    def from_dict(cls, data: object) -> ValidationCheck:
        if not isinstance(data, dict):
            raise LaunchError("Invalid validation check: expected mapping.")
        identifier = _optional_string(data.get("id")) or _optional_string(
            data.get("criterion_id")
        )
        status = normalize_validation_check_status(_string_value(data, "status"))
        criterion_id = _optional_string(data.get("criterion_id")) or (
            identifier if status != "not_run" else None
        )
        if status != "not_run" and criterion_id is None:
            raise LaunchError(
                "Validation checks must reference a criterion_id "
                "unless status is not_run."
            )
        return cls(
            id=identifier,
            criterion_id=criterion_id,
            name=_string_value(data, "name"),
            status=status,
            details=_optional_string(data.get("details")),
            evidence=_string_tuple(data.get("evidence")),
            waiver=CriterionWaiver.from_dict(data.get("waiver")),
        )


@dataclass(slots=True, frozen=True)
class TodoCollection:
    task_id: str
    todos: tuple[TaskTodo, ...] = ()
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "todos"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "task_id": self.task_id,
            "todos": [item.to_dict() for item in self.todos],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TodoCollection:
        _require_contract(data, expected_object_type="todos")
        return cls(
            task_id=_string_value(data, "task_id"),
            todos=tuple(
                TaskTodo.from_dict(item) for item in _dict_list(data.get("todos"))
            ),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class LinkCollection:
    task_id: str
    links: tuple[FileLink, ...] = ()
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "links"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "task_id": self.task_id,
            "links": [item.to_dict() for item in self.links],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> LinkCollection:
        _require_contract(data, expected_object_type="links")
        return cls(
            task_id=_string_value(data, "task_id"),
            links=tuple(
                FileLink.from_dict(item) for item in _dict_list(data.get("links"))
            ),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class RequirementCollection:
    task_id: str
    requirements: tuple[DependencyRequirement, ...] = ()
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "requirements"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "task_id": self.task_id,
            "requirements": [item.to_dict() for item in self.requirements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RequirementCollection:
        _require_contract(data, expected_object_type="requirements")
        return cls(
            task_id=_string_value(data, "task_id"),
            requirements=tuple(
                DependencyRequirement.from_dict(item)
                for item in _dict_list(data.get("requirements"))
            ),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class TaskRecord:
    id: str
    slug: str
    title: str
    body: str
    status_stage: TaskStatusStage = "draft"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    description_summary: str | None = None
    priority: str | None = None
    labels: tuple[str, ...] = ()
    owner: str | None = None
    introduction_ref: str | None = None
    requirements: tuple[str, ...] = ()
    file_links: tuple[FileLink, ...] = ()
    todos: tuple[TaskTodo, ...] = ()
    latest_plan_version: int | None = None
    accepted_plan_version: int | None = None
    latest_planning_run: str | None = None
    latest_implementation_run: str | None = None
    latest_validation_run: str | None = None
    code_change_log_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "task"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "status": self.status_stage,
            "status_stage": self.status_stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description_summary": self.description_summary,
            "priority": self.priority,
            "labels": list(self.labels),
            "owner": self.owner,
            "intro_refs": list(self.intro_refs),
            "introduction_ref": self.introduction_ref,
            "requirements": list(self.requirements),
            "file_links": [item.to_dict() for item in self.file_links],
            "todos": [item.to_dict() for item in self.todos],
            "latest_plan": self.latest_plan,
            "latest_plan_version": self.latest_plan_version,
            "accepted_plan": self.accepted_plan,
            "accepted_plan_version": self.accepted_plan_version,
            "latest_planning_run": self.latest_planning_run,
            "latest_implementation_run": self.latest_implementation_run,
            "latest_validation_run": self.latest_validation_run,
            "code_change_log_refs": list(self.code_change_log_refs),
            "notes": list(self.notes),
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskRecord:
        _require_contract(data, expected_object_type="task")
        return cls(
            id=_string_value(data, "id"),
            slug=_string_value(data, "slug"),
            title=_string_value(data, "title"),
            body=_optional_string(data.get("body")) or "",
            status_stage=normalize_task_status_stage(
                _optional_string(data.get("status"))
                or _string_value(data, "status_stage")
            ),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            description_summary=_optional_string(data.get("description_summary")),
            priority=_optional_string(data.get("priority")),
            labels=_string_tuple(data.get("labels")),
            owner=_optional_string(data.get("owner")),
            introduction_ref=_optional_string(data.get("introduction_ref"))
            or _first_string(data.get("intro_refs")),
            requirements=_string_tuple(data.get("requirements")),
            file_links=tuple(
                FileLink.from_dict(item) for item in _dict_list(data.get("file_links"))
            ),
            todos=tuple(
                TaskTodo.from_dict(item) for item in _dict_list(data.get("todos"))
            ),
            latest_plan_version=_optional_int(data.get("latest_plan_version"))
            or _plan_version_value(data.get("latest_plan")),
            accepted_plan_version=_optional_int(data.get("accepted_plan_version"))
            or _plan_version_value(data.get("accepted_plan")),
            latest_planning_run=_optional_string(data.get("latest_planning_run")),
            latest_implementation_run=_optional_string(
                data.get("latest_implementation_run")
            ),
            latest_validation_run=_optional_string(data.get("latest_validation_run")),
            code_change_log_refs=_string_tuple(data.get("code_change_log_refs")),
            notes=_string_tuple(data.get("notes")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )

    @property
    def status(self) -> TaskStatusStage:
        return self.status_stage

    @property
    def intro_refs(self) -> tuple[str, ...]:
        return (self.introduction_ref,) if self.introduction_ref else ()

    @property
    def latest_plan(self) -> str | None:
        if self.latest_plan_version is None:
            return None
        return _plan_id(self.latest_plan_version)

    @property
    def accepted_plan(self) -> str | None:
        if self.accepted_plan_version is None:
            return None
        return _plan_id(self.accepted_plan_version)


@dataclass(slots=True, frozen=True)
class IntroductionRecord:
    id: str
    slug: str
    title: str
    body: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    labels: tuple[str, ...] = ()
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "intro"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "labels": list(self.labels),
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> IntroductionRecord:
        _require_contract(data, expected_object_type="intro")
        return cls(
            id=_string_value(data, "id"),
            slug=_string_value(data, "slug"),
            title=_string_value(data, "title"),
            body=_optional_string(data.get("body")) or "",
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            labels=_string_tuple(data.get("labels")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class PlanRecord:
    task_id: str
    plan_version: int
    body: str
    status: PlanStatus = "proposed"
    created_at: str = field(default_factory=utc_now_iso)
    created_by: ActorRef = field(default_factory=ActorRef)
    supersedes: int | None = None
    question_refs: tuple[str, ...] = ()
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    criteria: tuple[AcceptanceCriterion, ...] = ()
    todos: tuple[TaskTodo, ...] = ()
    generation_reason: str | None = None
    based_on_question_ids: tuple[str, ...] = ()
    based_on_answer_hash: str | None = None
    approved_at: str | None = None
    approved_by: ActorRef | None = None
    approval_note: str | None = None
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "plan"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "version": self.plan_version,
            "plan_version": self.plan_version,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by.to_dict(),
            "supersedes": self.supersedes,
            "question_refs": list(self.question_refs),
            "criteria": [item.to_dict() for item in self.criteria],
            "todos": [item.to_dict() for item in self.todos],
            "generation_reason": self.generation_reason,
            "based_on_question_ids": list(self.based_on_question_ids),
            "based_on_answer_hash": self.based_on_answer_hash,
            "supersedes_plan_id": (
                _plan_id(self.supersedes) if self.supersedes is not None else None
            ),
            "approved_at": self.approved_at,
            "approved_by": (
                self.approved_by.to_dict() if self.approved_by is not None else None
            ),
            "approval_note": self.approval_note,
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlanRecord:
        _require_contract(data, expected_object_type="plan")
        plan_version = (
            _optional_int(data.get("plan_version"))
            or _optional_int(data.get("version"))
            or _plan_version_from_id(_optional_string(data.get("plan_id")))
        )
        if plan_version is None:
            raise LaunchError("Missing or invalid 'plan_version' value.")
        return cls(
            task_id=_string_value(data, "task_id"),
            plan_version=plan_version,
            body=_optional_string(data.get("body")) or "",
            status=normalize_plan_status(_string_value(data, "status")),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            created_by=ActorRef.from_dict(data.get("created_by")),
            supersedes=_optional_int(data.get("supersedes")),
            question_refs=_string_tuple(data.get("question_refs")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            criteria=tuple(
                AcceptanceCriterion.from_dict(item)
                for item in _dict_list(data.get("criteria"))
            ),
            todos=tuple(
                TaskTodo.from_dict(item) for item in _dict_list(data.get("todos"))
            ),
            generation_reason=_optional_string(data.get("generation_reason")),
            based_on_question_ids=(
                _string_tuple(data.get("based_on_question_ids"))
                or _string_tuple(data.get("question_refs"))
            ),
            based_on_answer_hash=_optional_string(data.get("based_on_answer_hash")),
            approved_at=_optional_string(data.get("approved_at")),
            approved_by=ActorRef.from_dict(data.get("approved_by"))
            if data.get("approved_by") is not None
            else None,
            approval_note=_optional_string(data.get("approval_note")),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )

    @property
    def plan_id(self) -> str:
        return _plan_id(self.plan_version)


@dataclass(slots=True, frozen=True)
class QuestionRecord:
    id: str
    task_id: str
    question: str
    plan_version: int | None = None
    status: QuestionStatus = "open"
    created_at: str = field(default_factory=utc_now_iso)
    answered_at: str | None = None
    answered_by: str | None = None
    answered_by_actor: ActorRef | None = None
    asked_by_actor: ActorRef | None = None
    asked_in_harness: HarnessRef | None = None
    required_for_plan: bool = False
    answer_source: str | None = None
    answer: str | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "question"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "id": self.id,
            "task_id": self.task_id,
            "plan_version": self.plan_version,
            "status": self.status,
            "created_at": self.created_at,
            "answered_at": self.answered_at,
            "answered_by": self.answered_by,
            "answered_by_actor": (
                self.answered_by_actor.to_dict()
                if self.answered_by_actor is not None
                else None
            ),
            "asked_by_actor": (
                self.asked_by_actor.to_dict()
                if self.asked_by_actor is not None
                else None
            ),
            "asked_in_harness": (
                self.asked_in_harness.to_dict()
                if self.asked_in_harness is not None
                else None
            ),
            "required_for_plan": self.required_for_plan,
            "answer_source": self.answer_source,
            "question": self.question,
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> QuestionRecord:
        _require_contract(data, expected_object_type="question")
        return cls(
            id=_string_value(data, "id"),
            task_id=_string_value(data, "task_id"),
            question=_string_value(data, "question"),
            plan_version=_optional_int(data.get("plan_version")),
            status=normalize_question_status(_string_value(data, "status")),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            answered_at=_optional_string(data.get("answered_at")),
            answered_by=_optional_string(data.get("answered_by")),
            answered_by_actor=ActorRef.from_dict(data.get("answered_by_actor"))
            if data.get("answered_by_actor") is not None
            else None,
            asked_by_actor=ActorRef.from_dict(data.get("asked_by_actor"))
            if data.get("asked_by_actor") is not None
            else None,
            asked_in_harness=HarnessRef.from_dict(data.get("asked_in_harness"))
            if data.get("asked_in_harness") is not None
            else None,
            required_for_plan=bool(data.get("required_for_plan", False)),
            answer_source=_optional_string(data.get("answer_source")),
            answer=_optional_string(data.get("answer")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class TaskRunRecord:
    run_id: str
    task_id: str
    run_type: RunType
    status: RunStatus = "running"
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    actor: ActorRef = field(default_factory=ActorRef)
    harness: HarnessRef | None = None
    based_on_plan_version: int | None = None
    based_on_implementation_run: str | None = None
    resumes_run_id: str | None = None
    summary: str | None = None
    worklog: tuple[str, ...] = ()
    deviations_from_plan: tuple[str, ...] = ()
    change_refs: tuple[str, ...] = ()
    todo_updates: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    checks: tuple[ValidationCheck, ...] = ()
    evidence: tuple[str, ...] = ()
    recommendation: str | None = None
    result: ValidationResult | None = None
    handoff_refs: tuple[str, ...] = ()
    actor_history: tuple[ActorRef, ...] = ()
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    based_on_plan: str | None = None
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "run"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "run_type": self.run_type,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "actor": self.actor.to_dict(),
            "harness": self.harness.to_dict() if self.harness is not None else None,
            "based_on_plan": self.based_on_plan or self.plan_ref,
            "based_on_plan_version": self.based_on_plan_version,
            "based_on_implementation_run": self.based_on_implementation_run,
            "resumes_run_id": self.resumes_run_id,
            "summary": self.summary,
            "worklog": list(self.worklog),
            "deviations_from_plan": list(self.deviations_from_plan),
            "change_refs": list(self.change_refs),
            "todo_updates": list(self.todo_updates),
            "artifact_refs": list(self.artifact_refs),
            "checks": [item.to_dict() for item in self.checks],
            "evidence": list(self.evidence),
            "recommendation": self.recommendation,
            "result": self.result,
            "handoff_refs": list(self.handoff_refs),
            "actor_history": [item.to_dict() for item in self.actor_history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskRunRecord:
        _require_contract(data, expected_object_type="run")
        result = _optional_string(data.get("result"))
        return cls(
            run_id=_string_value(data, "run_id"),
            task_id=_string_value(data, "task_id"),
            run_type=normalize_run_type(_string_value(data, "run_type")),
            status=normalize_run_status(_string_value(data, "status")),
            started_at=_optional_string(data.get("started_at")) or utc_now_iso(),
            finished_at=_optional_string(data.get("finished_at")),
            actor=ActorRef.from_dict(data.get("actor")),
            harness=HarnessRef.from_dict(data.get("harness"))
            if data.get("harness") is not None
            else None,
            based_on_plan_version=_optional_int(data.get("based_on_plan_version"))
            or _plan_version_value(data.get("based_on_plan")),
            based_on_implementation_run=_optional_string(
                data.get("based_on_implementation_run")
            ),
            resumes_run_id=_optional_string(data.get("resumes_run_id")),
            summary=_optional_string(data.get("summary")),
            worklog=_string_tuple(data.get("worklog")),
            deviations_from_plan=_string_tuple(data.get("deviations_from_plan")),
            change_refs=_string_tuple(data.get("change_refs")),
            todo_updates=_string_tuple(data.get("todo_updates")),
            artifact_refs=_string_tuple(data.get("artifact_refs")),
            checks=tuple(
                ValidationCheck.from_dict(item)
                for item in _dict_list(data.get("checks"))
            ),
            evidence=_string_tuple(data.get("evidence")),
            recommendation=_optional_string(data.get("recommendation")),
            result=normalize_validation_result(result) if result is not None else None,
            handoff_refs=_string_tuple(data.get("handoff_refs")),
            actor_history=tuple(
                ActorRef.from_dict(item)
                for item in _dict_list(data.get("actor_history"))
            ),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            based_on_plan=_optional_string(data.get("based_on_plan")),
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )

    @property
    def plan_ref(self) -> str | None:
        if self.based_on_plan_version is None:
            return None
        return _plan_id(self.based_on_plan_version)


@dataclass(slots=True, frozen=True)
class CodeChangeRecord:
    change_id: str
    task_id: str
    implementation_run: str
    timestamp: str
    kind: str
    path: str
    summary: str
    git_commit: str | None = None
    git_diff_stat: str | None = None
    command: str | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    exit_code: int | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "change"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "change_id": self.change_id,
            "task_id": self.task_id,
            "implementation_run": self.implementation_run,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "path": self.path,
            "summary": self.summary,
            "git_commit": self.git_commit,
            "git_diff_stat": self.git_diff_stat,
            "command": self.command,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CodeChangeRecord:
        _require_contract(data, expected_object_type="change")
        return cls(
            change_id=_string_value(data, "change_id"),
            task_id=_string_value(data, "task_id"),
            implementation_run=_string_value(data, "implementation_run"),
            timestamp=_optional_string(data.get("timestamp")) or utc_now_iso(),
            kind=_string_value(data, "kind"),
            path=_string_value(data, "path"),
            summary=_string_value(data, "summary"),
            git_commit=_optional_string(data.get("git_commit")),
            git_diff_stat=_optional_string(data.get("git_diff_stat")),
            command=_optional_string(data.get("command")),
            before_hash=_optional_string(data.get("before_hash")),
            after_hash=_optional_string(data.get("after_hash")),
            exit_code=_optional_int(data.get("exit_code")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


@dataclass(slots=True, frozen=True)
class TaskLock:
    lock_id: str
    task_id: str
    stage: ActiveTaskStatusStage
    run_id: str
    created_at: str
    expires_at: str | None
    reason: str
    holder: ActorRef
    lease_seconds: int = 7200
    last_heartbeat_at: str | None = None
    broken_at: str | None = None
    broken_by: ActorRef | None = None
    broken_reason: str | None = None
    actor: ActorRef | None = None
    harness: HarnessRef | None = None
    transfer_history: tuple[tuple[str, str, str], ...] = ()
    transfer_date: str | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "lock"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "lock_id": self.lock_id,
            "task_id": self.task_id,
            "stage": self.stage,
            "run_type": self.run_type,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "lease_seconds": self.lease_seconds,
            "last_heartbeat_at": self.last_heartbeat_at,
            "reason": self.reason,
            "holder": self.holder.to_dict(),
            "broken_at": self.broken_at,
            "broken_by": (
                self.broken_by.to_dict() if self.broken_by is not None else None
            ),
            "broken_reason": self.broken_reason,
            "actor": self.actor.to_dict() if self.actor is not None else None,
            "harness": self.harness.to_dict() if self.harness is not None else None,
            "transfer_history": [list(entry) for entry in self.transfer_history],
            "transfer_date": self.transfer_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskLock:
        _require_contract(data, expected_object_type="lock")
        stage = _lock_stage_from_data(data)
        if stage not in {"planning", "implementing", "validating"}:
            raise LaunchError(f"Unsupported lock stage: {stage}")

        # Deserialize transfer_history
        transfer_history_data = data.get("transfer_history", [])
        transfer_history: tuple[tuple[str, str, str], ...] = ()
        if isinstance(transfer_history_data, list):
            for entry in transfer_history_data:
                if isinstance(entry, list | tuple) and len(entry) == 3:
                    transfer_history = transfer_history + (tuple(entry),)

        return cls(
            lock_id=_string_value(data, "lock_id"),
            task_id=_string_value(data, "task_id"),
            stage=cast(ActiveTaskStatusStage, stage),
            run_id=_string_value(data, "run_id"),
            created_at=_string_value(data, "created_at"),
            expires_at=_optional_string(data.get("expires_at")),
            reason=_string_value(data, "reason"),
            holder=ActorRef.from_dict(data.get("holder")),
            lease_seconds=_optional_int(data.get("lease_seconds")) or 7200,
            last_heartbeat_at=_optional_string(data.get("last_heartbeat_at")),
            broken_at=_optional_string(data.get("broken_at")),
            broken_by=ActorRef.from_dict(data.get("broken_by"))
            if data.get("broken_by") is not None
            else None,
            broken_reason=_optional_string(data.get("broken_reason")),
            actor=ActorRef.from_dict(data.get("actor"))
            if data.get("actor") is not None
            else None,
            harness=HarnessRef.from_dict(data.get("harness"))
            if data.get("harness") is not None
            else None,
            transfer_history=transfer_history,
            transfer_date=_optional_string(data.get("transfer_date")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )

    @property
    def run_type(self) -> RunType:
        return cast(
            RunType,
            {
                "planning": "planning",
                "implementing": "implementation",
                "validating": "validation",
            }[self.stage],
        )


@dataclass(slots=True, frozen=True)
class TaskEvent:
    ts: str
    event: str
    task_id: str
    actor: ActorRef
    harness: HarnessRef | None = None
    event_id: str = field(
        default_factory=lambda: (
            "evt-"
            + utc_now_iso().replace(":", "").replace("-", "").replace("+00:00", "Z")
        )
    )
    data: dict[str, object] = field(default_factory=dict)
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "event"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "event_id": self.event_id,
            "ts": self.ts,
            "event": self.event,
            "task_id": self.task_id,
            "actor": self.actor.to_dict(),
            "harness": self.harness.to_dict() if self.harness is not None else None,
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskEvent:
        _require_contract(data, expected_object_type="event")
        payload = data.get("data")
        return cls(
            event_id=_string_value(data, "event_id"),
            ts=_string_value(data, "ts"),
            event=_string_value(data, "event"),
            task_id=_string_value(data, "task_id"),
            actor=ActorRef.from_dict(data.get("actor")),
            harness=HarnessRef.from_dict(data.get("harness"))
            if data.get("harness") is not None
            else None,
            data=payload if isinstance(payload, dict) else {},
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_list_string(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, str)] or None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _string_value(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise LaunchError(f"Missing or invalid '{key}' value.")
    return value


def _int_value(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise LaunchError(f"Missing or invalid '{key}' value.")
    return value


def _first_string(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, str):
            return item
    return None


def _plan_id(version: int) -> str:
    return f"plan-v{version}"


def _plan_version_from_id(value: str | None) -> int | None:
    if value is None or not value.startswith("plan-v"):
        return None
    suffix = value.removeprefix("plan-v")
    return int(suffix) if suffix.isdigit() else None


def _plan_version_value(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _plan_version_from_id(value)
    return None


def _lock_stage_from_data(data: dict[str, object]) -> TaskStatusStage:
    stage = _optional_string(data.get("stage"))
    if stage is None:
        run_type = _optional_string(data.get("run_type"))
        stage = {
            "planning": "planning",
            "implementation": "implementing",
            "validation": "validating",
        }.get(run_type or "")
    if stage is None:
        raise LaunchError("Missing or invalid 'stage' value.")
    return normalize_task_status_stage(stage)


def _generated_event_id() -> str:
    timestamp = utc_now_iso().replace(":", "").replace("-", "").replace("+00:00", "Z")
    return f"evt-{timestamp}"


def _require_contract(data: dict[str, object], *, expected_object_type: str) -> None:
    version = data.get("schema_version")
    if not isinstance(version, int) or version > TASKLEDGER_SCHEMA_VERSION:
        raise LaunchError(
            "Unsupported schema version: "
            f"expected <= {TASKLEDGER_SCHEMA_VERSION}, got {version!r}."
        )
    object_type = _optional_string(data.get("object_type"))
    if object_type != expected_object_type:
        raise LaunchError(
            "Missing or invalid 'object_type': "
            f"expected {expected_object_type!r}, got {object_type!r}."
        )
    if "file_version" in data:
        _require_v2_file_version(data)


def _int_or_default(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _require_v2_file_version(data: dict[str, object]) -> None:
    version = _optional_string(data.get("file_version"))
    if version != TASKLEDGER_V2_FILE_VERSION:
        raise LaunchError(
            "Unsupported file version: "
            f"expected {TASKLEDGER_V2_FILE_VERSION}, got {version!r}."
        )
