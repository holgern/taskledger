from __future__ import annotations

import importlib
import inspect

import pytest


@pytest.mark.parametrize(
    ("module_name", "function_names"),
    [
        (
            "taskledger.api.contexts",
            (
                "save_context",
                "list_contexts",
                "resolve_context",
                "rename_context",
                "delete_context",
                "build_context_for_item",
            ),
        ),
        (
            "taskledger.api.items",
            (
                "create_item",
                "list_items",
                "show_item",
                "approve_item",
                "reopen_item",
                "close_item",
                "item_summary",
                "build_item_work_prompt",
                "start_item_work",
                "complete_item_stage",
                "refine_item",
            ),
        ),
        (
            "taskledger.api.memories",
            (
                "create_memory",
                "list_memories",
                "resolve_memory",
                "read_memory_body",
                "refresh_memory",
                "rename_memory",
                "update_memory_body",
                "write_memory_body",
                "update_memory_tags",
                "delete_memory",
            ),
        ),
        (
            "taskledger.api.repos",
            (
                "add_repo",
                "list_repos",
                "resolve_repo",
                "resolve_repo_root",
                "remove_repo",
                "set_repo_role",
                "set_default_execution_repo",
                "clear_default_execution_repo",
            ),
        ),
        (
            "taskledger.api.runs",
            (
                "list_runs",
                "show_run",
                "delete_run",
                "cleanup_runs",
                "promote_run_output",
                "promote_run_report",
                "apply_run_result",
            ),
        ),
        (
            "taskledger.api.validation",
            (
                "list_validation_records",
                "append_validation_record",
                "remove_validation_records",
            ),
        ),
        (
            "taskledger.api.workflows",
            (
                "list_workflows",
                "resolve_workflow",
                "save_workflow_definition",
                "delete_workflow_definition",
                "default_workflow_id",
                "set_default_workflow",
                "assign_item_workflow",
                "item_workflow_state",
                "item_stage_records",
                "latest_stage_record",
                "allowed_stage_transitions",
                "can_enter_stage",
                "enter_stage",
                "mark_stage_running",
                "mark_stage_succeeded",
                "mark_stage_failed",
                "mark_stage_needs_review",
                "approve_stage",
            ),
        ),
        (
            "taskledger.api.execution_requests",
            (
                "build_execution_request",
                "expand_execution_request",
                "record_execution_outcome",
            ),
        ),
    ],
)
def test_workspace_root_first_argument(
    module_name: str, function_names: tuple[str, ...]
) -> None:
    module = importlib.import_module(module_name)
    for function_name in function_names:
        function = getattr(module, function_name)
        params = list(inspect.signature(function).parameters.values())
        assert params
        assert params[0].name == "workspace_root"


@pytest.mark.parametrize(
    ("module_name", "forbidden_names"),
    [
        (
            "taskledger.api.contexts",
            ("load_contexts", "save_context_entry", "save_contexts"),
        ),
        (
            "taskledger.api.memories",
            ("load_memories", "memory_body_path", "save_memories"),
        ),
        (
            "taskledger.api.repos",
            ("load_repos", "save_repos"),
        ),
        (
            "taskledger.api.runs",
            ("create_run_dir", "save_run_record", "load_run_records"),
        ),
        (
            "taskledger.api.validation",
            (
                "load_validation_records",
                "save_validation_records",
                "validation_records_dir",
                "validation_records_index_path",
            ),
        ),
    ],
)
def test_api_modules_do_not_expose_paths_helpers(
    module_name: str, forbidden_names: tuple[str, ...]
) -> None:
    module = importlib.import_module(module_name)
    for name in forbidden_names:
        assert not hasattr(module, name)


def test_compose_module_removed_in_favor_of_composition() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("taskledger.api.compose")

    composition = importlib.import_module("taskledger.api.composition")
    runtime_support = importlib.import_module("taskledger.api.runtime_support")
    types_module = importlib.import_module("taskledger.api.types")

    assert composition is not None
    assert runtime_support is not None
    assert types_module is not None
