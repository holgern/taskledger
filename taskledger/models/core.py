from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

from taskledger.models.execution import ExecutionOutcomeRecord, ExecutionPreviewRecord

MemoryUpdateMode = Literal["replace", "append", "prepend"]
ContextSourceKind = Literal["memory", "file", "item", "inline", "loop_artifact"]
ProjectRepoKind = Literal["odoo", "enterprise", "custom", "shared", "generic"]
ProjectStage = Literal["analysis", "state", "plan", "implementation", "validation"]
WorkflowStatus = Literal[
    "draft",
    "ready",
    "in_progress",
    "blocked",
    "waiting_approval",
    "waiting_validation",
    "completed",
    "closed",
]
WorkflowStageStatus = Literal[
    "not_started",
    "ready",
    "running",
    "succeeded",
    "failed",
    "needs_review",
    "skipped",
]
WorkflowTransitionRule = Literal[
    "create",
    "approve",
    "stage_succeeded",
    "stage_failed",
    "human_override",
    "close",
]
WorkItemStatus = Literal[
    "draft",
    "planned",
    "approved",
    "in_progress",
    "implemented",
    "validated",
    "closed",
    "rejected",
]
WorkItemStage = Literal[
    "intake",
    "planning",
    "approval",
    "execution",
    "validation",
    "closure",
]

DEFAULT_PROJECT_SOURCE_MAX_CHARS = 12000
DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS = 48000
DEFAULT_PROJECT_SOURCE_HEAD_LINES = 200
DEFAULT_PROJECT_SOURCE_TAIL_LINES = 50
ARTIFACT_MEMORY_REF_FIELDS = (
    "analysis_memory_ref",
    "state_memory_ref",
    "plan_memory_ref",
    "implementation_memory_ref",
    "validation_memory_ref",
    "save_target_ref",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True, frozen=True)
class ProjectConfig:
    default_memory_update_mode: MemoryUpdateMode = "replace"
    default_save_run_reports: bool = True
    default_source_max_chars: int | None = DEFAULT_PROJECT_SOURCE_MAX_CHARS
    default_total_source_max_chars: int | None = DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS
    default_source_head_lines: int | None = DEFAULT_PROJECT_SOURCE_HEAD_LINES
    default_source_tail_lines: int | None = DEFAULT_PROJECT_SOURCE_TAIL_LINES
    default_context_order: tuple[str, ...] = (
        "memory",
        "file",
        "item",
        "inline",
        "loop_artifact",
    )
    workflow_schema: str | None = None
    project_context: str | None = None
    artifact_rules: tuple[ProjectArtifactRule, ...] = ()
    default_artifact_order: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ProjectArtifactRule:
    name: str
    depends_on: tuple[str, ...] = ()
    memory_ref_field: str | None = None
    label: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "depends_on": list(self.depends_on),
            "memory_ref_field": self.memory_ref_field,
            "label": self.label,
            "description": self.description,
        }


@dataclass(slots=True, frozen=True)
class ProjectPaths:
    workspace_root: Path
    project_dir: Path
    config_path: Path
    repos_dir: Path
    repo_index_path: Path
    workflows_dir: Path
    workflow_index_path: Path
    memories_dir: Path
    memory_index_path: Path
    contexts_dir: Path
    context_index_path: Path
    items_dir: Path
    item_index_path: Path
    stages_dir: Path
    stage_index_path: Path
    runs_dir: Path


@dataclass(slots=True, frozen=True)
class ProjectRepo:
    name: str
    slug: str
    path: str
    kind: ProjectRepoKind
    branch: str | None
    notes: str | None
    created_at: str
    updated_at: str
    role: Literal["read", "write", "both"] = "read"
    preferred_for_execution: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "slug": self.slug,
            "path": self.path,
            "kind": self.kind,
            "branch": self.branch,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "role": self.role,
            "preferred_for_execution": self.preferred_for_execution,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectRepo:
        kind = _string_value(data, "kind")
        if kind not in {"odoo", "enterprise", "custom", "shared", "generic"}:
            raise ValueError(f"Unsupported project repo kind: {kind}")
        role = _optional_string_value(data, "role") or "read"
        if role not in {"read", "write", "both"}:
            raise ValueError(f"Unsupported project repo role: {role}")
        return cls(
            name=_string_value(data, "name"),
            slug=_string_value(data, "slug"),
            path=_string_value(data, "path"),
            kind=cast(ProjectRepoKind, kind),
            branch=_optional_string_value(data, "branch"),
            notes=_optional_string_value(data, "notes"),
            created_at=_string_value(data, "created_at"),
            updated_at=_string_value(data, "updated_at"),
            role=cast(Literal["read", "write", "both"], role),
            preferred_for_execution=bool(data.get("preferred_for_execution", False)),
        )


@dataclass(slots=True, frozen=True)
class ProjectMemory:
    id: str
    name: str
    slug: str
    path: str
    tags: tuple[str, ...]
    summary: str | None
    created_at: str
    updated_at: str
    source_run_id: str | None
    content_hash: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "path": self.path,
            "tags": list(self.tags),
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_run_id": self.source_run_id,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectMemory:
        return cls(
            id=_string_value(data, "id"),
            name=_string_value(data, "name"),
            slug=_string_value(data, "slug"),
            path=_string_value(data, "path"),
            tags=_string_tuple(data.get("tags")),
            summary=_optional_string_value(data, "summary"),
            created_at=_string_value(data, "created_at"),
            updated_at=_string_value(data, "updated_at"),
            source_run_id=_optional_string_value(data, "source_run_id"),
            content_hash=_optional_string_value(data, "content_hash"),
        )


@dataclass(slots=True, frozen=True)
class ProjectContextEntry:
    name: str
    slug: str
    path: str
    memory_refs: tuple[str, ...]
    file_refs: tuple[str, ...]
    item_refs: tuple[str, ...]
    inline_texts: tuple[str, ...]
    loop_latest_refs: tuple[str, ...]
    summary: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "slug": self.slug,
            "path": self.path,
            "memory_refs": list(self.memory_refs),
            "file_refs": list(self.file_refs),
            "item_refs": list(self.item_refs),
            "inline_texts": list(self.inline_texts),
            "loop_latest_refs": list(self.loop_latest_refs),
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectContextEntry:
        return cls(
            name=_string_value(data, "name"),
            slug=_string_value(data, "slug"),
            path=_string_value(data, "path"),
            memory_refs=_string_tuple(data.get("memory_refs")),
            file_refs=_string_tuple(data.get("file_refs")),
            item_refs=_string_tuple(data.get("item_refs")),
            inline_texts=_string_tuple(data.get("inline_texts")),
            loop_latest_refs=_string_tuple(data.get("loop_latest_refs")),
            summary=_optional_string_value(data, "summary"),
            created_at=_string_value(data, "created_at"),
            updated_at=_string_value(data, "updated_at"),
        )


@dataclass(slots=True, frozen=True)
class ProjectSourceBudget:
    max_source_chars: int | None = None
    max_total_chars: int | None = None
    head_lines: int | None = None
    tail_lines: int | None = None
    line_start: int | None = None
    line_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "max_source_chars": self.max_source_chars,
            "max_total_chars": self.max_total_chars,
            "head_lines": self.head_lines,
            "tail_lines": self.tail_lines,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass(slots=True, frozen=True)
class ProjectWorkItem:
    id: str
    slug: str
    title: str
    description: str
    source_path: str | None
    repo_refs: tuple[str, ...]
    target_repo_ref: str | None
    status: WorkItemStatus
    stage: WorkItemStage
    created_at: str
    updated_at: str
    approved_at: str | None = None
    closed_at: str | None = None
    discovered_file_refs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    validation_checklist: tuple[str, ...] = ()
    notes: str | None = None
    estimate: str | None = None
    owner: str | None = None
    labels: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    analysis_memory_ref: str | None = None
    state_memory_ref: str | None = None
    plan_memory_ref: str | None = None
    implementation_memory_ref: str | None = None
    validation_memory_ref: str | None = None
    linked_memories: tuple[str, ...] = ()
    linked_runs: tuple[str, ...] = ()
    linked_loop_tasks: tuple[str, ...] = ()
    save_target_ref: str | None = None
    workflow_id: str | None = None
    current_stage_id: str | None = None
    workflow_status: WorkflowStatus = "draft"
    stage_status: WorkflowStageStatus | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "source_path": self.source_path,
            "repo_refs": list(self.repo_refs),
            "target_repo_ref": self.target_repo_ref,
            "status": self.status,
            "stage": self.stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "closed_at": self.closed_at,
            "discovered_file_refs": list(self.discovered_file_refs),
            "acceptance_criteria": list(self.acceptance_criteria),
            "validation_checklist": list(self.validation_checklist),
            "notes": self.notes,
            "estimate": self.estimate,
            "owner": self.owner,
            "labels": list(self.labels),
            "depends_on": list(self.depends_on),
            "analysis_memory_ref": self.analysis_memory_ref,
            "state_memory_ref": self.state_memory_ref,
            "plan_memory_ref": self.plan_memory_ref,
            "implementation_memory_ref": self.implementation_memory_ref,
            "validation_memory_ref": self.validation_memory_ref,
            "linked_memories": list(self.linked_memories),
            "linked_runs": list(self.linked_runs),
            "linked_loop_tasks": list(self.linked_loop_tasks),
            "save_target_ref": self.save_target_ref,
            "workflow_id": self.workflow_id,
            "current_stage_id": self.current_stage_id,
            "workflow_status": self.workflow_status,
            "stage_status": self.stage_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectWorkItem:
        status = _string_value(data, "status")
        if status not in {
            "draft",
            "planned",
            "approved",
            "in_progress",
            "implemented",
            "validated",
            "closed",
            "rejected",
        }:
            raise ValueError(f"Unsupported work item status: {status}")
        stage = _string_value(data, "stage")
        if stage not in {
            "intake",
            "planning",
            "approval",
            "execution",
            "validation",
            "closure",
        }:
            raise ValueError(f"Unsupported work item stage: {stage}")
        workflow_status = _optional_string_value(data, "workflow_status")
        if workflow_status is None:
            workflow_status = _legacy_workflow_status(status)
        if workflow_status not in {
            "draft",
            "ready",
            "in_progress",
            "blocked",
            "waiting_approval",
            "waiting_validation",
            "completed",
            "closed",
        }:
            raise ValueError(f"Unsupported workflow status: {workflow_status}")
        stage_status = _optional_string_value(data, "stage_status")
        if stage_status is None:
            stage_status = _legacy_stage_status(status)
        if stage_status is not None and stage_status not in {
            "not_started",
            "ready",
            "running",
            "succeeded",
            "failed",
            "needs_review",
            "skipped",
        }:
            raise ValueError(f"Unsupported stage status: {stage_status}")
        return cls(
            id=_string_value(data, "id"),
            slug=_string_value(data, "slug"),
            title=_string_value(data, "title"),
            description=_string_value(data, "description"),
            source_path=_optional_string_value(data, "source_path"),
            repo_refs=_string_tuple(data.get("repo_refs")),
            target_repo_ref=_optional_string_value(data, "target_repo_ref"),
            status=cast(WorkItemStatus, status),
            stage=cast(WorkItemStage, stage),
            created_at=_string_value(data, "created_at"),
            updated_at=_string_value(data, "updated_at"),
            approved_at=_optional_string_value(data, "approved_at"),
            closed_at=_optional_string_value(data, "closed_at"),
            discovered_file_refs=_string_tuple(data.get("discovered_file_refs")),
            acceptance_criteria=_string_tuple(data.get("acceptance_criteria")),
            validation_checklist=_string_tuple(data.get("validation_checklist")),
            notes=_optional_string_value(data, "notes"),
            estimate=_optional_string_value(data, "estimate"),
            owner=_optional_string_value(data, "owner"),
            labels=_string_tuple(data.get("labels")),
            depends_on=_string_tuple(data.get("depends_on")),
            analysis_memory_ref=_optional_string_value(data, "analysis_memory_ref"),
            state_memory_ref=_optional_string_value(data, "state_memory_ref"),
            plan_memory_ref=_optional_string_value(data, "plan_memory_ref"),
            implementation_memory_ref=_optional_string_value(
                data,
                "implementation_memory_ref",
            ),
            validation_memory_ref=_optional_string_value(
                data,
                "validation_memory_ref",
            ),
            linked_memories=_string_tuple(data.get("linked_memories")),
            linked_runs=_string_tuple(data.get("linked_runs")),
            linked_loop_tasks=_string_tuple(data.get("linked_loop_tasks")),
            save_target_ref=_optional_string_value(data, "save_target_ref"),
            workflow_id=_optional_string_value(data, "workflow_id"),
            current_stage_id=_optional_string_value(data, "current_stage_id"),
            workflow_status=cast(WorkflowStatus, workflow_status),
            stage_status=cast(WorkflowStageStatus | None, stage_status),
        )


@dataclass(slots=True, frozen=True)
class ContextSource:
    kind: ContextSourceKind
    ref: str
    title: str | None
    body: str
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "title": self.title,
            "body": self.body,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ContextSource:
        kind = _string_value(data, "kind")
        if kind not in {"memory", "file", "item", "inline", "loop_artifact"}:
            raise ValueError(f"Unsupported context source kind: {kind}")
        metadata = data.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("Context source metadata must be a mapping when provided.")
        return cls(
            kind=cast(ContextSourceKind, kind),
            ref=_string_value(data, "ref"),
            title=_optional_string_value(data, "title"),
            body=_string_value(data, "body"),
            metadata=metadata,
        )


@dataclass(slots=True, frozen=True)
class ContextBundle:
    name: str | None
    sources: tuple[ContextSource, ...]
    composed_text: str
    content_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "sources": [item.to_dict() for item in self.sources],
            "composed_text": self.composed_text,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ContextBundle:
        raw_sources = data.get("sources")
        if raw_sources is None:
            raw_sources = []
        if not isinstance(raw_sources, list):
            raise ValueError("Context bundle sources must be a list.")
        return cls(
            name=_optional_string_value(data, "name"),
            sources=tuple(
                ContextSource.from_dict(item)
                for item in raw_sources
                if isinstance(item, dict)
            ),
            composed_text=_string_value(data, "composed_text"),
            content_hash=_string_value(data, "content_hash"),
        )


@dataclass(slots=True, frozen=True)
class ProjectRunRecord:
    run_id: str
    started_at: str
    finished_at: str
    memory_inputs: tuple[str, ...]
    file_inputs: tuple[str, ...]
    item_inputs: tuple[str, ...]
    inline_inputs: tuple[str, ...]
    context_inputs: tuple[str, ...]
    loop_artifact_inputs: tuple[str, ...]
    save_target: str | None
    save_mode: MemoryUpdateMode | None
    stage: ProjectStage | None
    repo_refs: tuple[str, ...]
    context_hash: str
    status: str
    result_path: str
    preview_path: str
    prompt_path: str
    composed_prompt_path: str
    report_path: str | None
    run_in_repo: str | None = None
    run_in_repo_source: str | None = None
    context_repo_refs: tuple[str, ...] = ()
    origin: str | None = None
    harness: str | None = None
    resolved_model: str | None = None
    prompt_summary: str | None = None
    output_summary: str | None = None
    source_summary: dict[str, object] | None = None
    prompt_diagnostics: dict[str, object] | None = None
    git_summary: dict[str, object] | None = None
    artifact_summary: dict[str, object] | None = None
    project_item_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "origin": self.origin,
            "harness": self.harness,
            "resolved_model": self.resolved_model,
            "prompt_summary": self.prompt_summary,
            "output_summary": self.output_summary,
            "source_summary": self.source_summary,
            "prompt_diagnostics": self.prompt_diagnostics,
            "git_summary": self.git_summary,
            "artifact_summary": self.artifact_summary,
            "memory_inputs": list(self.memory_inputs),
            "file_inputs": list(self.file_inputs),
            "item_inputs": list(self.item_inputs),
            "inline_inputs": list(self.inline_inputs),
            "context_inputs": list(self.context_inputs),
            "loop_artifact_inputs": list(self.loop_artifact_inputs),
            "save_target": self.save_target,
            "save_mode": self.save_mode,
            "project_item_ref": self.project_item_ref,
            "stage": self.stage,
            "repo_refs": list(self.repo_refs),
            "run_in_repo": self.run_in_repo,
            "run_in_repo_source": self.run_in_repo_source,
            "context_repo_refs": list(self.context_repo_refs),
            "context_hash": self.context_hash,
            "status": self.status,
            "result_path": self.result_path,
            "preview_path": self.preview_path,
            "prompt_path": self.prompt_path,
            "composed_prompt_path": self.composed_prompt_path,
            "report_path": self.report_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProjectRunRecord:
        save_mode = _optional_string_value(data, "save_mode")
        if save_mode is not None and save_mode not in {"replace", "append", "prepend"}:
            raise ValueError(f"Unsupported save mode: {save_mode}")
        stage = _normalize_project_stage_value(_optional_string_value(data, "stage"))
        if stage is not None and stage not in {
            "analysis",
            "state",
            "plan",
            "implementation",
            "validation",
        }:
            raise ValueError(f"Unsupported project stage: {stage}")
        return cls(
            run_id=_string_value(data, "run_id"),
            started_at=_string_value(data, "started_at"),
            finished_at=_string_value(data, "finished_at"),
            origin=_optional_string_value(data, "origin"),
            harness=_optional_string_value(data, "harness"),
            resolved_model=_optional_string_value(data, "resolved_model"),
            prompt_summary=_optional_string_value(data, "prompt_summary"),
            output_summary=_optional_string_value(data, "output_summary"),
            source_summary=_optional_dict_value(data, "source_summary"),
            prompt_diagnostics=_optional_dict_value(data, "prompt_diagnostics"),
            git_summary=_optional_dict_value(data, "git_summary"),
            artifact_summary=_optional_dict_value(data, "artifact_summary"),
            memory_inputs=_string_tuple(data.get("memory_inputs")),
            file_inputs=_string_tuple(data.get("file_inputs")),
            item_inputs=_string_tuple(data.get("item_inputs")),
            inline_inputs=_string_tuple(data.get("inline_inputs")),
            context_inputs=_string_tuple(data.get("context_inputs")),
            loop_artifact_inputs=_string_tuple(data.get("loop_artifact_inputs")),
            save_target=_optional_string_value(data, "save_target"),
            save_mode=cast(MemoryUpdateMode | None, save_mode),
            project_item_ref=_optional_string_value(data, "project_item_ref"),
            stage=cast(ProjectStage | None, stage),
            repo_refs=_string_tuple(data.get("repo_refs")),
            run_in_repo=_optional_string_value(data, "run_in_repo"),
            run_in_repo_source=_optional_string_value(data, "run_in_repo_source"),
            context_repo_refs=_string_tuple(data.get("context_repo_refs")),
            context_hash=_string_value(data, "context_hash"),
            status=_string_value(data, "status"),
            result_path=_string_value(data, "result_path"),
            preview_path=_string_value(data, "preview_path"),
            prompt_path=_string_value(data, "prompt_path"),
            composed_prompt_path=_string_value(data, "composed_prompt_path"),
            report_path=_optional_string_value(data, "report_path"),
        )


@dataclass(slots=True, frozen=True)
class WorkflowStageDefinition:
    stage_id: str
    label: str
    kind: str
    order: int
    requires_approval_before_entry: bool
    allows_human_completion: bool
    allows_runtime_execution: bool
    output_kind: str | None
    save_target_rule: str | None
    validation_rule: str | None
    instruction_template_id: str | None
    result_schema_id: str | None = None
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "label": self.label,
            "kind": self.kind,
            "order": self.order,
            "requires_approval_before_entry": self.requires_approval_before_entry,
            "allows_human_completion": self.allows_human_completion,
            "allows_runtime_execution": self.allows_runtime_execution,
            "output_kind": self.output_kind,
            "save_target_rule": self.save_target_rule,
            "validation_rule": self.validation_rule,
            "instruction_template_id": self.instruction_template_id,
            "result_schema_id": self.result_schema_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowStageDefinition:
        return cls(
            stage_id=_string_value(data, "stage_id"),
            label=_string_value(data, "label"),
            kind=_string_value(data, "kind"),
            order=_int_value(data, "order"),
            requires_approval_before_entry=_bool_value(
                data,
                "requires_approval_before_entry",
            ),
            allows_human_completion=_bool_value(data, "allows_human_completion"),
            allows_runtime_execution=_bool_value(data, "allows_runtime_execution"),
            output_kind=_optional_string_value(data, "output_kind"),
            save_target_rule=_optional_string_value(data, "save_target_rule"),
            validation_rule=_optional_string_value(data, "validation_rule"),
            instruction_template_id=_optional_string_value(
                data,
                "instruction_template_id",
            ),
            result_schema_id=_optional_string_value(data, "result_schema_id"),
            metadata=_optional_dict_value(data, "metadata"),
        )


@dataclass(slots=True, frozen=True)
class WorkflowTransition:
    from_stage: str | None
    to_stage: str
    rule: WorkflowTransitionRule
    condition: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "rule": self.rule,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowTransition:
        rule = _string_value(data, "rule")
        if rule not in {
            "create",
            "approve",
            "stage_succeeded",
            "stage_failed",
            "human_override",
            "close",
        }:
            raise ValueError(f"Unsupported workflow transition rule: {rule}")
        return cls(
            from_stage=_optional_string_value(data, "from_stage"),
            to_stage=_string_value(data, "to_stage"),
            rule=cast(WorkflowTransitionRule, rule),
            condition=_optional_string_value(data, "condition"),
        )


@dataclass(slots=True, frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: str
    default_for_items: bool
    stages: tuple[WorkflowStageDefinition, ...]
    transitions: tuple[WorkflowTransition, ...]
    next_action_policy: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "default_for_items": self.default_for_items,
            "stages": [stage.to_dict() for stage in self.stages],
            "transitions": [transition.to_dict() for transition in self.transitions],
            "next_action_policy": self.next_action_policy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowDefinition:
        return cls(
            workflow_id=_string_value(data, "workflow_id"),
            name=_string_value(data, "name"),
            version=_string_value(data, "version"),
            default_for_items=_bool_value(data, "default_for_items"),
            stages=tuple(
                WorkflowStageDefinition.from_dict(item)
                for item in _dict_list_value(data, "stages")
            ),
            transitions=tuple(
                WorkflowTransition.from_dict(item)
                for item in _dict_list_value(data, "transitions")
            ),
            next_action_policy=_optional_string_value(data, "next_action_policy"),
        )


@dataclass(slots=True, frozen=True)
class ItemWorkflowState:
    item_ref: str
    workflow_id: str
    current_stage_id: str | None
    workflow_status: WorkflowStatus
    stage_status: WorkflowStageStatus | None
    allowed_next_stages: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    pending_approvals: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "item_ref": self.item_ref,
            "workflow_id": self.workflow_id,
            "current_stage_id": self.current_stage_id,
            "workflow_status": self.workflow_status,
            "stage_status": self.stage_status,
            "allowed_next_stages": list(self.allowed_next_stages),
            "blocking_reasons": list(self.blocking_reasons),
            "pending_approvals": list(self.pending_approvals),
        }


@dataclass(slots=True, frozen=True)
class ItemStageRecord:
    record_id: str
    item_ref: str
    workflow_id: str
    stage_id: str
    status: str
    origin: str | None
    requested_by: str | None
    run_id: str | None
    validation_record_refs: tuple[str, ...] = ()
    input_snapshot_hash: str | None = None
    output_summary: str | None = None
    save_target: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "item_ref": self.item_ref,
            "workflow_id": self.workflow_id,
            "stage_id": self.stage_id,
            "status": self.status,
            "origin": self.origin,
            "requested_by": self.requested_by,
            "run_id": self.run_id,
            "validation_record_refs": list(self.validation_record_refs),
            "input_snapshot_hash": self.input_snapshot_hash,
            "output_summary": self.output_summary,
            "save_target": self.save_target,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ItemStageRecord:
        return cls(
            record_id=_string_value(data, "record_id"),
            item_ref=_string_value(data, "item_ref"),
            workflow_id=_string_value(data, "workflow_id"),
            stage_id=_string_value(data, "stage_id"),
            status=_string_value(data, "status"),
            origin=_optional_string_value(data, "origin"),
            requested_by=_optional_string_value(data, "requested_by"),
            run_id=_optional_string_value(data, "run_id"),
            validation_record_refs=_string_tuple(data.get("validation_record_refs")),
            input_snapshot_hash=_optional_string_value(data, "input_snapshot_hash"),
            output_summary=_optional_string_value(data, "output_summary"),
            save_target=_optional_string_value(data, "save_target"),
            created_at=_optional_string_value(data, "created_at"),
            updated_at=_optional_string_value(data, "updated_at"),
            metadata=_optional_dict_value(data, "metadata"),
        )


@dataclass(slots=True, frozen=True)
class ExecutionRequest:
    request_id: str
    item_ref: str
    workflow_id: str
    stage_id: str
    context_inputs: tuple[str, ...] = ()
    memory_inputs: tuple[str, ...] = ()
    file_inputs: tuple[str, ...] = ()
    item_inputs: tuple[str, ...] = ()
    inline_inputs: tuple[str, ...] = ()
    loop_artifact_inputs: tuple[str, ...] = ()
    instruction_template_id: str | None = None
    prompt_seed: str | None = None
    run_in_repo: str | None = None
    save_target: str | None = None
    save_mode: MemoryUpdateMode | None = None
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "item_ref": self.item_ref,
            "workflow_id": self.workflow_id,
            "stage_id": self.stage_id,
            "context_inputs": list(self.context_inputs),
            "memory_inputs": list(self.memory_inputs),
            "file_inputs": list(self.file_inputs),
            "item_inputs": list(self.item_inputs),
            "inline_inputs": list(self.inline_inputs),
            "loop_artifact_inputs": list(self.loop_artifact_inputs),
            "instruction_template_id": self.instruction_template_id,
            "prompt_seed": self.prompt_seed,
            "run_in_repo": self.run_in_repo,
            "save_target": self.save_target,
            "save_mode": self.save_mode,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ExecutionRequest:
        save_mode = _optional_string_value(data, "save_mode")
        if save_mode is not None and save_mode not in {"replace", "append", "prepend"}:
            raise ValueError(f"Unsupported save mode: {save_mode}")
        return cls(
            request_id=_string_value(data, "request_id"),
            item_ref=_string_value(data, "item_ref"),
            workflow_id=_string_value(data, "workflow_id"),
            stage_id=_string_value(data, "stage_id"),
            context_inputs=_string_tuple(data.get("context_inputs")),
            memory_inputs=_string_tuple(data.get("memory_inputs")),
            file_inputs=_string_tuple(data.get("file_inputs")),
            item_inputs=_string_tuple(data.get("item_inputs")),
            inline_inputs=_string_tuple(data.get("inline_inputs")),
            loop_artifact_inputs=_string_tuple(data.get("loop_artifact_inputs")),
            instruction_template_id=_optional_string_value(
                data,
                "instruction_template_id",
            ),
            prompt_seed=_optional_string_value(data, "prompt_seed"),
            run_in_repo=_optional_string_value(data, "run_in_repo"),
            save_target=_optional_string_value(data, "save_target"),
            save_mode=cast(MemoryUpdateMode | None, save_mode),
            metadata=_optional_dict_value(data, "metadata"),
        )


@dataclass(slots=True, frozen=True)
class ExpandedExecutionRequest:
    request: ExecutionRequest
    final_prompt: str
    composed_prompt: str
    sources: tuple[dict[str, object], ...]
    repo_refs: tuple[str, ...]
    run_in_repo: str | None
    save_target: str | None
    save_mode: MemoryUpdateMode | None
    source_summary: dict[str, object]
    context_hash: str | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "request": self.request.to_dict(),
            "final_prompt": self.final_prompt,
            "composed_prompt": self.composed_prompt,
            "sources": [dict(item) for item in self.sources],
            "repo_refs": list(self.repo_refs),
            "run_in_repo": self.run_in_repo,
            "save_target": self.save_target,
            "save_mode": self.save_mode,
            "source_summary": self.source_summary,
            "context_hash": self.context_hash,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ExpandedExecutionRequest:
        request_data = data.get("request")
        if not isinstance(request_data, dict):
            raise ValueError("Expanded execution request requires a request payload.")
        return cls(
            request=ExecutionRequest.from_dict(request_data),
            final_prompt=_string_value(data, "final_prompt"),
            composed_prompt=_string_value(data, "composed_prompt"),
            sources=tuple(_dict_list_value(data, "sources")),
            repo_refs=_string_tuple(data.get("repo_refs")),
            run_in_repo=_optional_string_value(data, "run_in_repo"),
            save_target=_optional_string_value(data, "save_target"),
            save_mode=cast(
                MemoryUpdateMode | None, _optional_string_value(data, "save_mode")
            ),
            source_summary=_dict_value(data, "source_summary"),
            context_hash=_optional_string_value(data, "context_hash"),
            warnings=_string_tuple(data.get("warnings")),
        )


@dataclass(slots=True, frozen=True)
class ProjectState:
    paths: ProjectPaths
    config_overrides: dict[str, object]
    repos: tuple[ProjectRepo, ...]
    memories: tuple[ProjectMemory, ...]
    contexts: tuple[ProjectContextEntry, ...]
    work_items: tuple[ProjectWorkItem, ...]
    recent_runs: tuple[ProjectRunRecord, ...]


@dataclass(slots=True, frozen=True)
class ProjectPreparedRun:
    user_prompt: str
    bundle: ContextBundle
    preview: ExecutionPreviewRecord
    source_budget: ProjectSourceBudget
    stage: ProjectStage | None
    repo_refs: tuple[str, ...]
    context_inputs: tuple[str, ...]
    memory_inputs: tuple[str, ...]
    file_inputs: tuple[str, ...]
    item_inputs: tuple[str, ...]
    inline_inputs: tuple[str, ...]
    loop_artifact_inputs: tuple[str, ...]
    save_target: str | None
    save_mode: MemoryUpdateMode | None
    origin: str | None = None
    run_in_repo: str | None = None
    run_in_repo_source: str | None = None
    context_repo_refs: tuple[str, ...] = ()
    prompt_diagnostics: dict[str, object] | None = None
    project_item_ref: str | None = None


@dataclass(slots=True, frozen=True)
class ProjectExecution:
    prepared: ProjectPreparedRun
    result: ExecutionOutcomeRecord
    record: ProjectRunRecord
    notices: tuple[str, ...]
    saved_memory: ProjectMemory | None


def _string_value(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key}")
    return value


def _required_string_value(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key}")
    return value


def _optional_string_value(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key}")
    return value


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def _normalize_project_stage_value(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = _ANSI_ESCAPE_RE.sub("", value)
    sanitized = _CONTROL_CHAR_RE.sub("", sanitized).strip()
    if sanitized == "implement":
        return "implementation"
    if sanitized in {"validate", "validate_summary"}:
        return "validation"
    return sanitized


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("Expected a list of strings.")
        result.append(item)
    return tuple(result)


def _optional_dict_value(data: dict[str, object], key: str) -> dict[str, object] | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {key}")
    return value


def _bool_value(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Expected boolean for {key}")
    return value


def _int_value(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Expected integer for {key}")
    return value


def _dict_value(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {key}")
    return value


def _dict_list_value(
    data: dict[str, object], key: str
) -> tuple[dict[str, object], ...]:
    value = data.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {key}")
    result: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Expected list of mappings for {key}")
        result.append(item)
    return tuple(result)


def _legacy_workflow_status(status: str) -> WorkflowStatus:
    if status in {"closed", "rejected"}:
        return "closed"
    if status == "validated":
        return "completed"
    if status in {"implemented", "in_progress"}:
        return "in_progress"
    if status == "approved":
        return "ready"
    if status == "planned":
        return "waiting_approval"
    return "draft"


def _legacy_stage_status(status: str) -> WorkflowStageStatus | None:
    if status in {"closed", "rejected"}:
        return "succeeded"
    if status == "validated":
        return "succeeded"
    if status in {"implemented", "in_progress"}:
        return "running"
    if status == "approved":
        return "ready"
    if status == "planned":
        return "succeeded"
    return "not_started"
