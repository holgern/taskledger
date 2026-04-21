from __future__ import annotations

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths, WorkflowDefinition
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import write_json as _write_json


def load_workflow_definitions(paths: ProjectPaths) -> list[WorkflowDefinition]:
    return [
        WorkflowDefinition.from_dict(item)
        for item in _load_json_array(
            paths.workflow_index_path, "workflow definition index"
        )
    ]


def save_workflow_definitions(
    paths: ProjectPaths,
    workflows: list[WorkflowDefinition],
) -> None:
    _write_json(
        paths.workflow_index_path, [workflow.to_dict() for workflow in workflows]
    )


def resolve_workflow_definition(
    paths: ProjectPaths,
    workflow_id: str,
) -> WorkflowDefinition:
    for workflow in load_workflow_definitions(paths):
        if workflow.workflow_id == workflow_id:
            return workflow
    raise LaunchError(f"Unknown workflow definition: {workflow_id}")


def delete_workflow_definition(
    paths: ProjectPaths, workflow_id: str
) -> WorkflowDefinition:
    workflows = load_workflow_definitions(paths)
    remaining = [
        workflow for workflow in workflows if workflow.workflow_id != workflow_id
    ]
    if len(remaining) == len(workflows):
        raise LaunchError(f"Unknown workflow definition: {workflow_id}")
    deleted = next(
        workflow for workflow in workflows if workflow.workflow_id == workflow_id
    )
    save_workflow_definitions(paths, remaining)
    return deleted
