from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectArtifactRule, ProjectConfig, ProjectState
from taskledger.storage import merge_project_config

_STATUS_ORDER = (
    "draft",
    "planned",
    "approved",
    "in_progress",
    "implemented",
    "validated",
    "closed",
    "rejected",
)
_DONE_DEPENDENCY_STATUSES = {"validated", "closed"}


def effective_workflow_config(state: ProjectState) -> ProjectConfig:
    return merge_project_config(ProjectConfig(), state.config_overrides)


def build_workflow_summary(state: ProjectState) -> dict[str, object] | None:
    config = effective_workflow_config(state)
    if not config.artifact_rules:
        return None
    rules = _ordered_rules(config)
    memory_state = _memory_completion_state(state)
    item_lookup = {item.id: item for item in state.work_items}
    item_states = [
        _item_workflow_state(
            item,
            rules=rules,
            item_lookup=item_lookup,
            memory_state=memory_state,
        )
        for item in state.work_items
    ]
    counts = {
        "ready": sum(1 for item in item_states if item["workflow_status"] == "ready"),
        "blocked": sum(
            1 for item in item_states if item["workflow_status"] == "blocked"
        ),
        "done": sum(1 for item in item_states if item["workflow_status"] == "done"),
    }
    return {
        "schema": config.workflow_schema,
        "project_context": config.project_context,
        "default_artifact_order": [rule.name for rule in rules],
        "artifact_rules": [rule.to_dict() for rule in rules],
        "counts": counts,
        "ready_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "ready"
        ],
        "blocked_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "blocked"
        ],
        "done_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "done"
        ],
        "items": item_states,
    }


def choose_next_workflow_item(state: ProjectState) -> dict[str, object] | None:
    workflow = build_workflow_summary(state)
    if workflow is None:
        return None
    items = workflow["items"]
    assert isinstance(items, list)
    ranked_ready = sorted(
        [
            item
            for item in items
            if isinstance(item, dict) and item.get("workflow_status") == "ready"
        ],
        key=_item_sort_key,
    )
    if ranked_ready:
        return ranked_ready[0]
    ranked_blocked = sorted(
        [
            item
            for item in items
            if isinstance(item, dict) and item.get("workflow_status") == "blocked"
        ],
        key=_item_sort_key,
    )
    if ranked_blocked:
        return ranked_blocked[0]
    return None


def _ordered_rules(config: ProjectConfig) -> tuple[ProjectArtifactRule, ...]:
    rule_map = {rule.name: rule for rule in config.artifact_rules}
    if config.default_artifact_order:
        ordered = [
            rule_map[name]
            for name in config.default_artifact_order
            if name in rule_map
        ]
        seen = {rule.name for rule in ordered}
        ordered.extend(
            rule for rule in config.artifact_rules if rule.name not in seen
        )
        return tuple(ordered)
    return config.artifact_rules


def _item_workflow_state(
    item,
    *,
    rules: tuple[ProjectArtifactRule, ...],
    item_lookup,
    memory_state: dict[str, bool],
) -> dict[str, object]:
    if item.status in {"closed", "rejected"}:
        workflow_status = "done"
        next_artifact = None
        next_artifact_status = None
        blocked_by: list[str] = []
    else:
        unresolved_dependencies = [
            dependency
            for dependency in item.depends_on
            if dependency not in item_lookup
            or item_lookup[dependency].status not in _DONE_DEPENDENCY_STATUSES
        ]
        (
            artifact_states,
            next_artifact,
            next_artifact_status,
            blocked_by,
        ) = _artifact_states_for_item(
            item,
            rules=rules,
            memory_state=memory_state,
            unresolved_dependencies=unresolved_dependencies,
        )
        if next_artifact is None:
            workflow_status = "ready"
        elif next_artifact_status == "blocked":
            workflow_status = "blocked"
        else:
            workflow_status = "ready"
        return {
            "item_ref": item.id,
            "item_slug": item.slug,
            "item_title": item.title,
            "item_status": item.status,
            "workflow_status": workflow_status,
            "item_dependencies": list(item.depends_on),
            "next_artifact": next_artifact,
            "next_artifact_status": next_artifact_status,
            "blocked_by": blocked_by,
            "artifacts": artifact_states,
        }
    artifact_states = [
        {
            "name": rule.name,
            "label": rule.label,
            "description": rule.description,
            "memory_ref_field": rule.memory_ref_field,
            "memory_ref": _memory_ref_for_rule(item, rule),
            "depends_on": list(rule.depends_on),
            "status": "done",
            "blocked_by": [],
            "complete": True,
        }
        for rule in rules
    ]
    return {
        "item_ref": item.id,
        "item_slug": item.slug,
        "item_title": item.title,
        "item_status": item.status,
        "workflow_status": workflow_status,
        "item_dependencies": list(item.depends_on),
        "next_artifact": next_artifact,
        "next_artifact_status": next_artifact_status,
        "blocked_by": blocked_by,
        "artifacts": artifact_states,
    }


def _artifact_states_for_item(
    item,
    *,
    rules: tuple[ProjectArtifactRule, ...],
    memory_state: dict[str, bool],
    unresolved_dependencies: list[str],
) -> tuple[list[dict[str, object]], str | None, str | None, list[str]]:
    states: list[dict[str, object]] = []
    done_rules: set[str] = set()
    next_artifact: str | None = None
    next_artifact_status: str | None = None
    next_blocked_by: list[str] = []
    for rule in rules:
        memory_ref = _memory_ref_for_rule(item, rule)
        complete = bool(memory_ref) and memory_state.get(memory_ref, False)
        blocked_by = [f"item:{ref}" for ref in unresolved_dependencies]
        blocked_by.extend(
            f"artifact:{dependency}"
            for dependency in rule.depends_on
            if dependency not in done_rules
        )
        if complete:
            status = "done"
            done_rules.add(rule.name)
        elif blocked_by:
            status = "blocked"
        else:
            status = "ready"
        states.append(
            {
                "name": rule.name,
                "label": rule.label,
                "description": rule.description,
                "memory_ref_field": rule.memory_ref_field,
                "memory_ref": memory_ref,
                "depends_on": list(rule.depends_on),
                "status": status,
                "blocked_by": blocked_by,
                "complete": complete,
            }
        )
        if next_artifact is None and not complete:
            next_artifact = rule.name
            next_artifact_status = status
            next_blocked_by = blocked_by
    return states, next_artifact, next_artifact_status, next_blocked_by


def _memory_ref_for_rule(item, rule: ProjectArtifactRule) -> str | None:
    if rule.memory_ref_field is None:
        return None
    value = getattr(item, rule.memory_ref_field, None)
    return value if isinstance(value, str) else None


def _memory_completion_state(state: ProjectState) -> dict[str, bool]:
    completion: dict[str, bool] = {}
    for memory in state.memories:
        completion[memory.id] = _memory_has_content(
            state.paths.project_dir / memory.path
        )
    return completion


def _memory_has_content(path: Path) -> bool:
    if not path.exists():
        return False
    return bool(path.read_text(encoding="utf-8").strip())


def _item_sort_key(item_state: dict[str, object]) -> tuple[int, str, str]:
    status = item_state.get("item_status")
    if not isinstance(status, str):
        status = "rejected"
    try:
        rank = _STATUS_ORDER.index(status)
    except ValueError:
        rank = len(_STATUS_ORDER)
    item_ref = item_state.get("item_ref")
    item_slug = item_state.get("item_slug")
    return (
        rank,
        item_ref if isinstance(item_ref, str) else "",
        item_slug if isinstance(item_slug, str) else "",
    )
