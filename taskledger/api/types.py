from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, cast

from taskledger.models import ContextSource as _ModelContextSource
from taskledger.models import (
    ContextSourceKind,
    ExecutionRequest,
    ExpandedExecutionRequest,
    ItemStageRecord,
    ItemWorkflowState,
    ProjectSourceBudget,
    WorkflowDefinition,
    WorkflowStageDefinition,
    WorkflowTransition,
)
from taskledger.models import ProjectConfig as _ProjectConfig
from taskledger.models import ProjectContextEntry as _ProjectContextEntry
from taskledger.models import ProjectMemory as _ProjectMemory
from taskledger.models import ProjectRepo as _ProjectRepo
from taskledger.models import ProjectRunRecord as _ProjectRunRecord
from taskledger.models import ProjectWorkItem as _ProjectWorkItem
from taskledger.models.execution import (
    ExecutionOutcomeRecord,
    ExecutionPreviewRecord,
    ExecutionStatus,
    TaskledgerExecutionOptions,
)

ContextEntry = _ProjectContextEntry
WorkItem = _ProjectWorkItem
Memory = _ProjectMemory
Repo = _ProjectRepo
RunRecord = _ProjectRunRecord
ProjectConfig = _ProjectConfig
ValidationRecord: TypeAlias = dict[str, object]
ExecutionOptions = TaskledgerExecutionOptions


@dataclass(slots=True, frozen=True)
class SourceBudget:
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

    def to_project_source_budget(self) -> ProjectSourceBudget:
        return ProjectSourceBudget(
            max_source_chars=self.max_source_chars,
            max_total_chars=self.max_total_chars,
            head_lines=self.head_lines,
            tail_lines=self.tail_lines,
            line_start=self.line_start,
            line_end=self.line_end,
        )

    @classmethod
    def from_project_source_budget(cls, budget: ProjectSourceBudget) -> SourceBudget:
        return cls(
            max_source_chars=budget.max_source_chars,
            max_total_chars=budget.max_total_chars,
            head_lines=budget.head_lines,
            tail_lines=budget.tail_lines,
            line_start=budget.line_start,
            line_end=budget.line_end,
        )


@dataclass(slots=True, frozen=True)
class ExpandedSelection:
    context_inputs: tuple[str, ...] = ()
    memory_inputs: tuple[str, ...] = ()
    file_inputs: tuple[str, ...] = ()
    item_inputs: tuple[str, ...] = ()
    inline_inputs: tuple[str, ...] = ()
    loop_artifact_inputs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "context_inputs": list(self.context_inputs),
            "memory_inputs": list(self.memory_inputs),
            "file_inputs": list(self.file_inputs),
            "item_inputs": list(self.item_inputs),
            "inline_inputs": list(self.inline_inputs),
            "loop_artifact_inputs": list(self.loop_artifact_inputs),
        }


@dataclass(slots=True, frozen=True)
class ContextSource:
    kind: str
    ref: str | None
    title: str | None
    repo_ref: str | None
    text: str
    truncated: bool = False
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "title": self.title,
            "repo_ref": self.repo_ref,
            "text": self.text,
            "truncated": self.truncated,
            "metadata": self.metadata,
        }

    def to_model(self) -> _ModelContextSource:
        metadata = dict(self.metadata or {})
        if self.repo_ref is not None and "repo" not in metadata:
            metadata["repo"] = self.repo_ref
        if self.truncated:
            metadata["truncated"] = True
        ref = self.ref or self.title or "source"
        return _ModelContextSource(
            kind=cast(ContextSourceKind, self.kind),
            ref=ref,
            title=self.title,
            body=self.text,
            metadata=metadata or None,
        )

    @classmethod
    def from_model(cls, source: _ModelContextSource) -> ContextSource:
        metadata = dict(source.metadata or {})
        repo = metadata.get("repo")
        repo_ref = repo if isinstance(repo, str) else None
        return cls(
            kind=source.kind,
            ref=source.ref,
            title=source.title,
            repo_ref=repo_ref,
            text=source.body,
            truncated=bool(metadata.get("truncated", False)),
            metadata=metadata or None,
        )


@dataclass(slots=True, frozen=True)
class ComposedBundle:
    prompt: str
    sources: tuple[ContextSource, ...]
    composed_text: str
    repo_refs: tuple[str, ...]
    content_hash: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "sources": [source.to_dict() for source in self.sources],
            "composed_text": self.composed_text,
            "repo_refs": list(self.repo_refs),
            "content_hash": self.content_hash,
        }


__all__ = [
    "ComposedBundle",
    "ContextEntry",
    "ContextSource",
    "ExecutionOptions",
    "ExecutionOutcomeRecord",
    "ExecutionRequest",
    "ExecutionPreviewRecord",
    "ExecutionStatus",
    "ExpandedExecutionRequest",
    "ExpandedSelection",
    "ItemStageRecord",
    "ItemWorkflowState",
    "Memory",
    "ProjectConfig",
    "Repo",
    "RunRecord",
    "SourceBudget",
    "ValidationRecord",
    "WorkflowDefinition",
    "WorkflowStageDefinition",
    "WorkflowTransition",
    "WorkItem",
]
