"""Guard the official API contract defined in API.md.

This suite enforces:
- documented module/symbol boundary contracts from API.md
- public callable signature compatibility (name/order/kind/defaults)
- DTO dataclass field-shape compatibility for exported API types
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import re
from pathlib import Path

import pytest

API_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "API.md"
API_CONTRACT_TEXT = API_CONTRACT_PATH.read_text(encoding="utf-8")


def _extract_h3_bullets(heading: str) -> tuple[str, ...]:
    match = re.search(
        rf"^### {re.escape(heading)}\n\n(?P<body>.*?)(?=^### |^## |\Z)",
        API_CONTRACT_TEXT,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"Missing API.md section: {heading!r}"
    return tuple(re.findall(r"^- `([^`]+)`\s*$", match.group("body"), re.MULTILINE))


def _extract_import_names(module_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"from {re.escape(module_name)} import \(\n(?P<body>.*?)\n\)",
        API_CONTRACT_TEXT,
        flags=re.DOTALL,
    )
    assert match, f"Missing import block for {module_name!r} in API.md"
    return tuple(
        re.findall(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*$",
            match.group("body"),
            re.MULTILINE,
        )
    )


def _extract_entity_contract() -> dict[str, tuple[str, ...]]:
    contract: dict[str, tuple[str, ...]] = {}
    for match in re.finditer(
        r"^### [^\n]*\(`(?P<module>taskledger\.api\.[^`]+)`\)\n\n"
        r"Canonical functions:\n\n(?P<body>.*?)(?=^### |^## |\Z)",
        API_CONTRACT_TEXT,
        flags=re.MULTILINE | re.DOTALL,
    ):
        module_name = match.group("module")
        names = tuple(
            re.findall(r"^- `([^`]+)`\s*$", match.group("body"), re.MULTILINE)
        )
        contract[module_name] = names
    return contract


ALLOWED_MODULES = _extract_h3_bullets("Allowed imports")
FORBIDDEN_MODULES = _extract_h3_bullets("Forbidden imports from runtildone")
TASKLEDGER_LOCAL_API_MODULES = _extract_h3_bullets(
    "Taskledger-local APIs (not in runtildone boundary)"
)
CLI_AND_PYTHON_MODULES = _extract_h3_bullets("CLI + Python")
PYTHON_ONLY_MODULES = _extract_h3_bullets("Extended CLI + Python")
ERROR_NAMES = _extract_import_names("taskledger.errors")
DTO_NAMES = _extract_import_names("taskledger.api.types")
ENTITY_CONTRACT = _extract_entity_contract()
COMPOSITION_NAMES = _extract_import_names("taskledger.api.composition")
RUNTIME_SUPPORT_NAMES = _extract_import_names("taskledger.api.runtime_support")


def test_api_contract_document_sections_are_parseable() -> None:
    assert ALLOWED_MODULES
    assert FORBIDDEN_MODULES
    assert TASKLEDGER_LOCAL_API_MODULES
    assert CLI_AND_PYTHON_MODULES
    assert PYTHON_ONLY_MODULES
    assert ERROR_NAMES
    assert DTO_NAMES
    assert ENTITY_CONTRACT
    assert COMPOSITION_NAMES
    assert RUNTIME_SUPPORT_NAMES


@pytest.mark.parametrize("module_name", ALLOWED_MODULES)
def test_allowed_module_is_importable(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None


@pytest.mark.parametrize("module_name", CLI_AND_PYTHON_MODULES)
def test_cli_and_python_modules_are_in_allowed_boundary(module_name: str) -> None:
    assert module_name in ALLOWED_MODULES


@pytest.mark.parametrize("module_name", PYTHON_ONLY_MODULES)
def test_python_only_modules_are_in_allowed_boundary(module_name: str) -> None:
    assert module_name in ALLOWED_MODULES


@pytest.mark.parametrize("module_name", TASKLEDGER_LOCAL_API_MODULES)
def test_taskledger_local_modules_are_importable_but_not_runtildone_boundary(
    module_name: str,
) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None
    assert module_name not in ALLOWED_MODULES


@pytest.mark.parametrize("module_name", FORBIDDEN_MODULES)
def test_forbidden_module_is_not_in_allowed_set(module_name: str) -> None:
    if module_name.endswith(".*"):
        prefix = module_name[:-2]
        assert prefix not in ALLOWED_MODULES
        assert all(
            not allowed.startswith(f"{prefix}.") for allowed in ALLOWED_MODULES
        )
        return
    assert module_name not in ALLOWED_MODULES


@pytest.mark.parametrize("name", ERROR_NAMES)
def test_error_import(name: str) -> None:
    from taskledger import errors

    assert hasattr(errors, name), f"taskledger.errors is missing {name}"
    assert issubclass(getattr(errors, name), Exception)


@pytest.mark.parametrize("name", DTO_NAMES)
def test_dto_import(name: str) -> None:
    from taskledger.api import types

    assert hasattr(types, name), f"taskledger.api.types is missing {name}"


@pytest.mark.parametrize(
    ("module_name", "expected_names"),
    [(m, names) for m, names in ENTITY_CONTRACT.items()],
    ids=[m.split(".")[-1] for m in ENTITY_CONTRACT],
)
def test_entity_api_has_all_canonical_functions(
    module_name: str, expected_names: tuple[str, ...]
) -> None:
    mod = importlib.import_module(module_name)
    missing = [n for n in expected_names if not hasattr(mod, n)]
    assert not missing, f"{module_name} is missing: {', '.join(missing)}"


@pytest.mark.parametrize("name", COMPOSITION_NAMES)
def test_composition_import(name: str) -> None:
    from taskledger.api import composition

    assert hasattr(composition, name), f"taskledger.api.composition is missing {name}"


@pytest.mark.parametrize("name", RUNTIME_SUPPORT_NAMES)
def test_runtime_support_import(name: str) -> None:
    from taskledger.api import runtime_support

    assert hasattr(runtime_support, name), (
        f"taskledger.api.runtime_support is missing {name}"
    )


def test_old_compose_module_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("taskledger.api.compose")


REQUIRED = object()
PK = inspect.Parameter.POSITIONAL_OR_KEYWORD
KO = inspect.Parameter.KEYWORD_ONLY
VK = inspect.Parameter.VAR_KEYWORD


SIGNATURE_CONTRACT = {
    "taskledger.api.contexts": {
        "save_context": (
            ("workspace_root", PK, REQUIRED),
            ("name", KO, REQUIRED),
            ("memory_refs", KO, ()),
            ("file_refs", KO, ()),
            ("directory_refs", KO, ()),
            ("item_refs", KO, ()),
            ("inline_texts", KO, ()),
            ("loop_latest_refs", KO, ()),
        ),
        "list_contexts": (("workspace_root", PK, REQUIRED),),
        "resolve_context": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "rename_context": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("new_name", KO, REQUIRED),
        ),
        "delete_context": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
    },
    "taskledger.api.items": {
        "create_item": (
            ("workspace_root", PK, REQUIRED),
            ("slug", KO, REQUIRED),
            ("description", KO, REQUIRED),
            ("repo_refs", KO, ()),
            ("source_path", KO, None),
            ("title", KO, None),
            ("target_repo_ref", KO, None),
        ),
        "list_items": (("workspace_root", PK, REQUIRED),),
        "show_item": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "update_item": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("title", KO, None),
            ("description", KO, None),
            ("notes", KO, None),
            ("owner", KO, None),
            ("estimate", KO, None),
            ("add_labels", KO, ()),
            ("remove_labels", KO, ()),
            ("add_dependencies", KO, ()),
            ("remove_dependencies", KO, ()),
            ("add_repo_refs", KO, ()),
            ("remove_repo_refs", KO, ()),
            ("target_repo_ref", KO, None),
            ("add_acceptance", KO, ()),
            ("remove_acceptance", KO, ()),
            ("add_validation_checks", KO, ()),
            ("remove_validation_checks", KO, ()),
            ("save_target_ref", KO, None),
        ),
        "approve_item": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "reopen_item": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "close_item": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "item_memory_refs": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
        ),
        "resolve_item_memory": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
        ),
        "read_item_memory_body": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
        ),
        "write_item_memory_body": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
            ("text", PK, REQUIRED),
            ("mode", KO, "replace"),
        ),
        "rename_item_memory": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
            ("new_name", KO, REQUIRED),
        ),
        "retag_item_memory": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
            ("add_tags", KO, ()),
            ("remove_tags", KO, ()),
        ),
        "delete_item_memory": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("role", PK, REQUIRED),
        ),
        "item_dossier": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("roles", KO, None),
            ("include_empty", KO, False),
            ("include_runs", KO, True),
            ("include_validation", KO, True),
            ("include_workflow", KO, True),
            ("include_contexts", KO, True),
        ),
        "render_item_dossier_markdown": (("dossier", PK, REQUIRED),),
        "next_action_payload": (("item", PK, REQUIRED),),
    },
    "taskledger.api.memories": {
        "create_memory": (
            ("workspace_root", PK, REQUIRED),
            ("name", KO, REQUIRED),
            ("body", KO, None),
            ("source_run_id", KO, None),
        ),
        "list_memories": (("workspace_root", PK, REQUIRED),),
        "resolve_memory": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "read_memory_body": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "refresh_memory": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "rename_memory": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("new_name", KO, REQUIRED),
        ),
        "write_memory_body": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("text", PK, REQUIRED),
            ("source_run_id", KO, None),
        ),
        "update_memory_body": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("text", PK, REQUIRED),
            ("mode", KO, "replace"),
            ("source_run_id", KO, None),
        ),
        "update_memory_tags": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("add_tags", KO, ()),
            ("remove_tags", KO, ()),
        ),
        "delete_memory": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
    },
    "taskledger.api.repos": {
        "add_repo": (
            ("workspace_root", PK, REQUIRED),
            ("kwargs", VK, REQUIRED),
        ),
        "list_repos": (("workspace_root", PK, REQUIRED),),
        "resolve_repo": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "resolve_repo_root": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "set_repo_role": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
            ("role", KO, REQUIRED),
        ),
        "set_default_execution_repo": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
        "clear_default_execution_repo": (("workspace_root", PK, REQUIRED),),
        "remove_repo": (
            ("workspace_root", PK, REQUIRED),
            ("ref", PK, REQUIRED),
        ),
    },
    "taskledger.api.runs": {
        "list_runs": (
            ("workspace_root", PK, REQUIRED),
            ("limit", KO, None),
        ),
        "show_run": (
            ("workspace_root", PK, REQUIRED),
            ("run_id", PK, REQUIRED),
        ),
        "delete_run": (
            ("workspace_root", PK, REQUIRED),
            ("run_id", PK, REQUIRED),
        ),
        "cleanup_runs": (
            ("workspace_root", PK, REQUIRED),
            ("keep", KO, REQUIRED),
        ),
        "promote_run_output": (
            ("workspace_root", PK, REQUIRED),
            ("run_id", PK, REQUIRED),
            ("name", KO, REQUIRED),
        ),
        "promote_run_report": (
            ("workspace_root", PK, REQUIRED),
            ("run_id", PK, REQUIRED),
            ("name", KO, REQUIRED),
        ),
        "summarize_run_inventory": (("workspace_root", PK, REQUIRED),),
    },
    "taskledger.api.validation": {
        "list_validation_records": (("workspace_root", PK, REQUIRED),),
        "append_validation_record": (
            ("workspace_root", PK, REQUIRED),
            ("kwargs", VK, REQUIRED),
        ),
        "remove_validation_records": (
            ("workspace_root", PK, REQUIRED),
            ("ids", KO, REQUIRED),
        ),
        "summarize_validation_records": (("workspace_root", PK, REQUIRED),),
    },
    "taskledger.api.workflows": {
        "list_workflows": (("workspace_root", PK, REQUIRED),),
        "resolve_workflow": (
            ("workspace_root", PK, REQUIRED),
            ("workflow_id", PK, REQUIRED),
        ),
        "save_workflow_definition": (
            ("workspace_root", PK, REQUIRED),
            ("workflow", PK, REQUIRED),
        ),
        "delete_workflow_definition": (
            ("workspace_root", PK, REQUIRED),
            ("workflow_id", PK, REQUIRED),
        ),
        "default_workflow_id": (("workspace_root", PK, REQUIRED),),
        "set_default_workflow": (
            ("workspace_root", PK, REQUIRED),
            ("workflow_id", PK, REQUIRED),
        ),
        "assign_item_workflow": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("workflow_id", PK, REQUIRED),
        ),
        "item_workflow_state": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
        ),
        "item_stage_records": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
        ),
        "latest_stage_record": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
        ),
        "allowed_stage_transitions": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
        ),
        "can_enter_stage": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
        ),
        "enter_stage": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("actor", KO, None),
        ),
        "mark_stage_running": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("request_id", KO, None),
        ),
        "mark_stage_succeeded": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("run_id", KO, None),
            ("summary", KO, None),
            ("save_target", KO, None),
            ("validation_record_refs", KO, ()),
        ),
        "mark_stage_failed": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("run_id", KO, None),
            ("summary", KO, None),
        ),
        "mark_stage_needs_review": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("reason", KO, None),
        ),
        "approve_stage": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", PK, REQUIRED),
            ("stage_id", PK, REQUIRED),
            ("actor", KO, None),
        ),
    },
    "taskledger.api.execution_requests": {
        "build_execution_request": (
            ("workspace_root", PK, REQUIRED),
            ("item_ref", KO, REQUIRED),
            ("stage_id", KO, REQUIRED),
            ("prompt", KO, None),
            ("repo_refs", KO, ()),
            ("memory_refs", KO, ()),
            ("file_refs", KO, ()),
            ("directory_refs", KO, ()),
            ("item_refs", KO, ()),
            ("inline_texts", KO, ()),
            ("loop_latest_refs", KO, ()),
            ("run_in_repo", KO, None),
            ("save_target", KO, None),
            ("save_mode", KO, None),
            ("file_render_mode", KO, None),
        ),
        "expand_execution_request": (
            ("workspace_root", PK, REQUIRED),
            ("request", KO, REQUIRED),
            ("options", KO, None),
        ),
        "record_execution_outcome": (
            ("workspace_root", PK, REQUIRED),
            ("request", KO, REQUIRED),
            ("outcome", KO, REQUIRED),
        ),
    },
    "taskledger.api.composition": {
        "expand_selection": (
            ("workspace_root", PK, REQUIRED),
            ("request", PK, REQUIRED),
        ),
        "build_sources": (
            ("workspace_root", PK, REQUIRED),
            ("selection", PK, REQUIRED),
            ("default_context_order", KO, ()),
            ("include_item_memories", KO, True),
            ("file_render_mode", KO, None),
            ("source_budget", KO, None),
        ),
        "compose_bundle": (
            ("prompt", PK, REQUIRED),
            ("sources", PK, REQUIRED),
        ),
        "describe_sources": (("sources", PK, REQUIRED),),
        "repo_refs_for_sources": (("sources", PK, REQUIRED),),
        "build_compose_payload": (
            ("context_name", KO, REQUIRED),
            ("prompt", KO, REQUIRED),
            ("explicit_inputs", KO, REQUIRED),
            ("file_render_mode", KO, "content"),
            ("selected_repo_refs", KO, REQUIRED),
            ("run_in_repo", KO, REQUIRED),
            ("source_budget", KO, REQUIRED),
            ("bundle", KO, REQUIRED),
        ),
    },
    "taskledger.api.runtime_support": {
        "get_effective_project_config": (
            ("workspace_root", PK, REQUIRED),
            ("base_config", KO, None),
        ),
        "create_run_artifact_layout": (
            ("workspace_root", PK, REQUIRED),
            ("origin", KO, REQUIRED),
        ),
        "save_run_record": (
            ("workspace_root", PK, REQUIRED),
            ("record", PK, REQUIRED),
        ),
        "resolve_repo_root": (
            ("workspace_root", PK, REQUIRED),
            ("repo_ref", PK, REQUIRED),
        ),
    },
}


WORKSPACE_ROOT_OPTIONAL_FUNCTIONS = {
    "taskledger.api.items.render_item_dossier_markdown",
    "taskledger.api.items.next_action_payload",
    "taskledger.api.composition.compose_bundle",
    "taskledger.api.composition.describe_sources",
    "taskledger.api.composition.repo_refs_for_sources",
    "taskledger.api.composition.build_compose_payload",
}


def _parameter_contract(
    fn: object,
) -> tuple[tuple[str, inspect._ParameterKind, object], ...]:
    sig = inspect.signature(fn)
    contract: list[tuple[str, inspect._ParameterKind, object]] = []
    for param in sig.parameters.values():
        default = (
            REQUIRED if param.default is inspect.Parameter.empty else param.default
        )
        contract.append((param.name, param.kind, default))
    return tuple(contract)


def _format_contract(
    contract: tuple[tuple[str, inspect._ParameterKind, object], ...],
) -> tuple[tuple[str, str, object], ...]:
    return tuple(
        (
            name,
            kind.name,
            "<required>" if default is REQUIRED else default,
        )
        for name, kind, default in contract
    )


@pytest.mark.parametrize(
    ("module_name", "function_name", "expected_contract"),
    [
        (module_name, function_name, expected)
        for module_name, functions in SIGNATURE_CONTRACT.items()
        for function_name, expected in functions.items()
    ],
    ids=[
        f"{module_name.split('.')[-1]}.{function_name}"
        for module_name, functions in SIGNATURE_CONTRACT.items()
        for function_name in functions
    ],
)
def test_public_callable_signature_contract(
    module_name: str,
    function_name: str,
    expected_contract: tuple[tuple[str, inspect._ParameterKind, object], ...],
) -> None:
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name)
    actual_contract = _parameter_contract(fn)
    assert actual_contract == expected_contract, (
        f"{module_name}.{function_name} signature changed.\n"
        f"expected: {_format_contract(expected_contract)}\n"
        f"actual:   {_format_contract(actual_contract)}"
    )


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    [
        (module_name, function_name)
        for module_name, functions in SIGNATURE_CONTRACT.items()
        for function_name in functions
    ],
    ids=[
        f"{module_name.split('.')[-1]}.{function_name}"
        for module_name, functions in SIGNATURE_CONTRACT.items()
        for function_name in functions
    ],
)
def test_workspace_root_first_argument_for_workspace_bound_entrypoints(
    module_name: str,
    function_name: str,
) -> None:
    fq_name = f"{module_name}.{function_name}"
    if fq_name in WORKSPACE_ROOT_OPTIONAL_FUNCTIONS:
        return
    module = importlib.import_module(module_name)
    params = list(inspect.signature(getattr(module, function_name)).parameters.values())
    assert params, f"{fq_name} unexpectedly has no parameters"
    assert params[0].name == "workspace_root", (
        f"{fq_name} must take workspace_root as first argument"
    )


DTO_FIELD_CONTRACT = {
    "ContextEntry": (
        "id",
        "name",
        "slug",
        "path",
        "memory_refs",
        "file_refs",
        "directory_refs",
        "item_refs",
        "inline_texts",
        "loop_latest_refs",
        "summary",
        "created_at",
        "updated_at",
    ),
    "WorkItem": (
        "id",
        "slug",
        "title",
        "description",
        "source_path",
        "repo_refs",
        "target_repo_ref",
        "status",
        "stage",
        "created_at",
        "updated_at",
        "approved_at",
        "closed_at",
        "discovered_file_refs",
        "acceptance_criteria",
        "validation_checklist",
        "notes",
        "estimate",
        "owner",
        "labels",
        "depends_on",
        "analysis_memory_ref",
        "state_memory_ref",
        "plan_memory_ref",
        "implementation_memory_ref",
        "validation_memory_ref",
        "linked_memories",
        "linked_runs",
        "linked_loop_tasks",
        "save_target_ref",
        "workflow_id",
        "current_stage_id",
        "workflow_status",
        "stage_status",
    ),
    "Memory": (
        "id",
        "name",
        "slug",
        "path",
        "tags",
        "summary",
        "created_at",
        "updated_at",
        "source_run_id",
        "content_hash",
    ),
    "Repo": (
        "name",
        "slug",
        "path",
        "kind",
        "branch",
        "notes",
        "created_at",
        "updated_at",
        "role",
        "preferred_for_execution",
    ),
    "RunRecord": (
        "run_id",
        "started_at",
        "finished_at",
        "memory_inputs",
        "file_inputs",
        "item_inputs",
        "inline_inputs",
        "context_inputs",
        "loop_artifact_inputs",
        "save_target",
        "save_mode",
        "stage",
        "repo_refs",
        "context_hash",
        "status",
        "result_path",
        "preview_path",
        "prompt_path",
        "composed_prompt_path",
        "report_path",
        "run_in_repo",
        "run_in_repo_source",
        "context_repo_refs",
        "origin",
        "harness",
        "resolved_model",
        "prompt_summary",
        "output_summary",
        "source_summary",
        "prompt_diagnostics",
        "git_summary",
        "artifact_summary",
        "project_item_ref",
    ),
    "ProjectConfig": (
        "default_memory_update_mode",
        "default_file_render_mode",
        "default_save_run_reports",
        "default_source_max_chars",
        "default_total_source_max_chars",
        "default_source_head_lines",
        "default_source_tail_lines",
        "default_context_order",
        "workflow_schema",
        "project_context",
        "artifact_rules",
        "default_artifact_order",
    ),
    "SourceBudget": (
        "max_source_chars",
        "max_total_chars",
        "head_lines",
        "tail_lines",
        "line_start",
        "line_end",
    ),
    "ExpandedSelection": (
        "context_inputs",
        "memory_inputs",
        "file_inputs",
        "directory_inputs",
        "item_inputs",
        "inline_inputs",
        "loop_artifact_inputs",
        "file_render_mode",
    ),
    "ContextSource": (
        "kind",
        "ref",
        "title",
        "repo_ref",
        "text",
        "truncated",
        "metadata",
    ),
    "ComposedBundle": (
        "prompt",
        "sources",
        "composed_text",
        "repo_refs",
        "content_hash",
    ),
    "ItemDossier": ("item_ref", "title", "sections", "metadata"),
    "ItemDossierSection": ("kind", "title", "ref", "body", "metadata"),
    "ExecutionOptions": (
        "harness_name",
        "model_hint",
        "config_file",
        "live_preview_default",
        "live_output",
        "render_live",
        "output_mode",
        "output_view",
        "primary_config_root",
        "template_root",
        "project_config",
        "extra",
    ),
    "ExecutionPreviewRecord": (
        "harness_name",
        "resolved_model",
        "command",
        "command_display",
        "run_cwd",
        "final_prompt",
        "prompt_hash",
        "prompt_preview",
        "original_chars",
        "final_chars",
        "original_prompt",
        "structured_output",
        "resolved_agent_name",
        "resolved_variant",
        "resolved_done_file",
        "resolved_prompt_template_file",
        "session_title",
        "final_message_path",
        "discovered_config_files",
        "primary_config_root",
        "value_sources",
        "harness_config_env",
        "provider_env",
        "env_keys_applied",
        "provider_settings",
        "provider_metadata",
        "templated",
        "done_file_suffix_injected",
        "prompt_after_template",
        "prompt_after_command_expansion",
        "expanded_commands",
        "read_roots",
        "write_roots",
        "harness_capabilities",
        "metadata",
    ),
    "ExecutionOutcomeRecord": (
        "harness",
        "status",
        "prompt",
        "cwd",
        "command",
        "returncode",
        "pid",
        "started_at",
        "finished_at",
        "duration_seconds",
        "completion_method",
        "stdout",
        "stderr",
        "done_file",
        "final_message",
        "session_id",
        "session_title",
        "provider_metadata",
        "terminal_event",
        "event_count",
        "stdout_bytes",
        "stderr_bytes",
        "runtime_warnings",
        "stdout_truncated",
        "stderr_truncated",
        "capture_strategy",
        "structured_output",
        "resolved_model",
        "resolved_agent_name",
        "resolved_variant",
        "resolved_prompt_template_file",
        "resolved_config_files",
        "resolved_primary_config_root",
        "resolved_value_sources",
        "prompt_hash",
        "prompt_preview",
        "prompt_token_estimate",
        "output_preview",
        "output_token_estimate",
        "total_token_estimate",
        "prompt_after_template",
        "prompt_after_command_expansion",
        "command_display",
        "env_keys_applied",
        "final_message_path_used",
        "stdout_transcript_path",
        "stderr_transcript_path",
        "event_transcript_path",
        "read_roots",
        "write_roots",
        "metadata",
    ),
    "WorkflowDefinition": (
        "workflow_id",
        "name",
        "version",
        "default_for_items",
        "stages",
        "transitions",
        "next_action_policy",
    ),
    "WorkflowStageDefinition": (
        "stage_id",
        "label",
        "kind",
        "order",
        "requires_approval_before_entry",
        "allows_human_completion",
        "allows_runtime_execution",
        "output_kind",
        "save_target_rule",
        "validation_rule",
        "instruction_template_id",
        "result_schema_id",
        "metadata",
    ),
    "WorkflowTransition": ("from_stage", "to_stage", "rule", "condition"),
    "ItemWorkflowState": (
        "item_ref",
        "workflow_id",
        "current_stage_id",
        "workflow_status",
        "stage_status",
        "allowed_next_stages",
        "blocking_reasons",
        "pending_approvals",
    ),
    "ItemStageRecord": (
        "record_id",
        "item_ref",
        "workflow_id",
        "stage_id",
        "status",
        "origin",
        "requested_by",
        "run_id",
        "validation_record_refs",
        "input_snapshot_hash",
        "output_summary",
        "save_target",
        "created_at",
        "updated_at",
        "metadata",
    ),
    "ExecutionRequest": (
        "request_id",
        "item_ref",
        "workflow_id",
        "stage_id",
        "context_inputs",
        "memory_inputs",
        "file_inputs",
        "directory_inputs",
        "item_inputs",
        "inline_inputs",
        "loop_artifact_inputs",
        "instruction_template_id",
        "prompt_seed",
        "run_in_repo",
        "save_target",
        "save_mode",
        "file_render_mode",
        "metadata",
    ),
    "ExpandedExecutionRequest": (
        "request",
        "final_prompt",
        "composed_prompt",
        "sources",
        "repo_refs",
        "run_in_repo",
        "save_target",
        "save_mode",
        "source_summary",
        "context_hash",
        "warnings",
    ),
}


@pytest.mark.parametrize("dto_name", tuple(DTO_FIELD_CONTRACT))
def test_dto_dataclass_field_shape_contract(dto_name: str) -> None:
    from taskledger.api import types

    dto = getattr(types, dto_name)
    assert dataclasses.is_dataclass(dto), f"{dto_name} must be a dataclass type"
    actual_fields = tuple(field.name for field in dataclasses.fields(dto))
    expected_fields = DTO_FIELD_CONTRACT[dto_name]
    assert actual_fields == expected_fields, (
        f"{dto_name} dataclass fields changed.\n"
        f"expected: {expected_fields}\n"
        f"actual:   {actual_fields}"
    )
