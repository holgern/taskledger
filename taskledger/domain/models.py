from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from taskledger.domain.states import (
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
    normalize_file_link_kind,
    normalize_plan_status,
    normalize_question_status,
    normalize_run_status,
    normalize_run_type,
    normalize_task_status_stage,
    normalize_validation_check_status,
    normalize_validation_result,
)
from taskledger.errors import LaunchError
from taskledger.models import utc_now_iso


@dataclass(slots=True, frozen=True)
class ActorRef:
    actor_type: Literal["agent", "user", "system"] = "agent"
    actor_name: str = "taskledger"
    host: str | None = None
    pid: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "host": self.host,
            "pid": self.pid,
        }

    @classmethod
    def from_dict(cls, data: object) -> ActorRef:
        if not isinstance(data, dict):
            return cls()
        actor_type = _optional_string(data.get("actor_type")) or "agent"
        if actor_type not in {"agent", "user", "system"}:
            raise LaunchError(f"Unsupported actor type: {actor_type}")
        pid = data.get("pid")
        return cls(
            actor_type=cast(Literal["agent", "user", "system"], actor_type),
            actor_name=_optional_string(data.get("actor_name")) or "taskledger",
            host=_optional_string(data.get("host")),
            pid=pid if isinstance(pid, int) else None,
        )


@dataclass(slots=True, frozen=True)
class FileLink:
    path: str
    kind: FileLinkKind = "code"
    label: str | None = None
    required_for_validation: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind,
            "label": self.label,
            "required_for_validation": self.required_for_validation,
        }

    @classmethod
    def from_dict(cls, data: object) -> FileLink:
        if not isinstance(data, dict):
            raise LaunchError("Invalid file link: expected mapping.")
        return cls(
            path=_string_value(data, "path"),
            kind=normalize_file_link_kind(_string_value(data, "kind")),
            label=_optional_string(data.get("label")),
            required_for_validation=bool(data.get("required_for_validation", False)),
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

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "mandatory": self.mandatory,
        }

    @classmethod
    def from_dict(cls, data: object) -> TaskTodo:
        if not isinstance(data, dict):
            raise LaunchError("Invalid todo: expected mapping.")
        return cls(
            id=_string_value(data, "id"),
            text=_string_value(data, "text"),
            done=bool(data.get("done", False)),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            source=_optional_string(data.get("source")),
            mandatory=bool(data.get("mandatory", False)),
        )


@dataclass(slots=True, frozen=True)
class ValidationCheck:
    name: str
    status: ValidationCheckStatus = "pass"
    details: str | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, data: object) -> ValidationCheck:
        if not isinstance(data, dict):
            raise LaunchError("Invalid validation check: expected mapping.")
        return cls(
            name=_string_value(data, "name"),
            status=normalize_validation_check_status(_string_value(data, "status")),
            details=_optional_string(data.get("details")),
            evidence=_string_tuple(data.get("evidence")),
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

    def to_dict(self) -> dict[str, object]:
        return {
            "file_version": self.file_version,
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "status_stage": self.status_stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description_summary": self.description_summary,
            "priority": self.priority,
            "labels": list(self.labels),
            "owner": self.owner,
            "introduction_ref": self.introduction_ref,
            "requirements": list(self.requirements),
            "file_links": [item.to_dict() for item in self.file_links],
            "todos": [item.to_dict() for item in self.todos],
            "latest_plan_version": self.latest_plan_version,
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
        _require_v2_file_version(data)
        return cls(
            id=_string_value(data, "id"),
            slug=_string_value(data, "slug"),
            title=_string_value(data, "title"),
            body=_optional_string(data.get("body")) or "",
            status_stage=normalize_task_status_stage(
                _string_value(data, "status_stage")
            ),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            description_summary=_optional_string(data.get("description_summary")),
            priority=_optional_string(data.get("priority")),
            labels=_string_tuple(data.get("labels")),
            owner=_optional_string(data.get("owner")),
            introduction_ref=_optional_string(data.get("introduction_ref")),
            requirements=_string_tuple(data.get("requirements")),
            file_links=tuple(
                FileLink.from_dict(item) for item in _dict_list(data.get("file_links"))
            ),
            todos=tuple(
                TaskTodo.from_dict(item) for item in _dict_list(data.get("todos"))
            ),
            latest_plan_version=_optional_int(data.get("latest_plan_version")),
            accepted_plan_version=_optional_int(data.get("accepted_plan_version")),
            latest_planning_run=_optional_string(data.get("latest_planning_run")),
            latest_implementation_run=_optional_string(
                data.get("latest_implementation_run")
            ),
            latest_validation_run=_optional_string(data.get("latest_validation_run")),
            code_change_log_refs=_string_tuple(data.get("code_change_log_refs")),
            notes=_string_tuple(data.get("notes")),
        )


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

    def to_dict(self) -> dict[str, object]:
        return {
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
        _require_v2_file_version(data)
        return cls(
            id=_string_value(data, "id"),
            slug=_string_value(data, "slug"),
            title=_string_value(data, "title"),
            body=_optional_string(data.get("body")) or "",
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            labels=_string_tuple(data.get("labels")),
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

    def to_dict(self) -> dict[str, object]:
        return {
            "file_version": self.file_version,
            "task_id": self.task_id,
            "plan_version": self.plan_version,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by.to_dict(),
            "supersedes": self.supersedes,
            "question_refs": list(self.question_refs),
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlanRecord:
        _require_v2_file_version(data)
        return cls(
            task_id=_string_value(data, "task_id"),
            plan_version=_int_value(data, "plan_version"),
            body=_optional_string(data.get("body")) or "",
            status=normalize_plan_status(_string_value(data, "status")),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            created_by=ActorRef.from_dict(data.get("created_by")),
            supersedes=_optional_int(data.get("supersedes")),
            question_refs=_string_tuple(data.get("question_refs")),
        )


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
    answer: str | None = None
    file_version: str = TASKLEDGER_V2_FILE_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "file_version": self.file_version,
            "id": self.id,
            "task_id": self.task_id,
            "plan_version": self.plan_version,
            "status": self.status,
            "created_at": self.created_at,
            "answered_at": self.answered_at,
            "answered_by": self.answered_by,
            "question": self.question,
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> QuestionRecord:
        _require_v2_file_version(data)
        return cls(
            id=_string_value(data, "id"),
            task_id=_string_value(data, "task_id"),
            question=_string_value(data, "question"),
            plan_version=_optional_int(data.get("plan_version")),
            status=normalize_question_status(_string_value(data, "status")),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            answered_at=_optional_string(data.get("answered_at")),
            answered_by=_optional_string(data.get("answered_by")),
            answer=_optional_string(data.get("answer")),
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
    based_on_plan_version: int | None = None
    based_on_implementation_run: str | None = None
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
    file_version: str = TASKLEDGER_V2_FILE_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "file_version": self.file_version,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "run_type": self.run_type,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "actor": self.actor.to_dict(),
            "based_on_plan_version": self.based_on_plan_version,
            "based_on_implementation_run": self.based_on_implementation_run,
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
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskRunRecord:
        _require_v2_file_version(data)
        result = _optional_string(data.get("result"))
        return cls(
            run_id=_string_value(data, "run_id"),
            task_id=_string_value(data, "task_id"),
            run_type=normalize_run_type(_string_value(data, "run_type")),
            status=normalize_run_status(_string_value(data, "status")),
            started_at=_optional_string(data.get("started_at")) or utc_now_iso(),
            finished_at=_optional_string(data.get("finished_at")),
            actor=ActorRef.from_dict(data.get("actor")),
            based_on_plan_version=_optional_int(data.get("based_on_plan_version")),
            based_on_implementation_run=_optional_string(
                data.get("based_on_implementation_run")
            ),
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
        )


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

    def to_dict(self) -> dict[str, object]:
        return {
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
        _require_v2_file_version(data)
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
    file_version: str = TASKLEDGER_V2_FILE_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "file_version": self.file_version,
            "lock_id": self.lock_id,
            "task_id": self.task_id,
            "stage": self.stage,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "reason": self.reason,
            "holder": self.holder.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskLock:
        _require_v2_file_version(data)
        stage = normalize_task_status_stage(_string_value(data, "stage"))
        if stage not in {"planning", "implementing", "validating"}:
            raise LaunchError(f"Unsupported lock stage: {stage}")
        return cls(
            lock_id=_string_value(data, "lock_id"),
            task_id=_string_value(data, "task_id"),
            stage=cast(ActiveTaskStatusStage, stage),
            run_id=_string_value(data, "run_id"),
            created_at=_string_value(data, "created_at"),
            expires_at=_optional_string(data.get("expires_at")),
            reason=_string_value(data, "reason"),
            holder=ActorRef.from_dict(data.get("holder")),
        )


@dataclass(slots=True, frozen=True)
class TaskEvent:
    ts: str
    event: str
    task_id: str
    actor: ActorRef
    data: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "ts": self.ts,
            "event": self.event,
            "task_id": self.task_id,
            "actor": self.actor.to_dict(),
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TaskEvent:
        payload = data.get("data")
        return cls(
            ts=_string_value(data, "ts"),
            event=_string_value(data, "event"),
            task_id=_string_value(data, "task_id"),
            actor=ActorRef.from_dict(data.get("actor")),
            data=payload if isinstance(payload, dict) else {},
        )


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


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


def _require_v2_file_version(data: dict[str, object]) -> None:
    version = _optional_string(data.get("file_version"))
    if version != TASKLEDGER_V2_FILE_VERSION:
        raise LaunchError(
            "Unsupported file version: "
            f"expected {TASKLEDGER_V2_FILE_VERSION}, got {version!r}."
        )
