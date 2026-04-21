"""Guard the official API contract defined in API.md.

Every name listed in API.md sections 1-7 must be importable from its declared
module.  If a function or type is accidentally removed or renamed, the
corresponding test here will fail with a clear message naming the missing
symbol.
"""

from __future__ import annotations

import importlib

import pytest

# ---------------------------------------------------------------------------
# Section 1 – Import boundary (allowed modules)
# ---------------------------------------------------------------------------

ALLOWED_MODULES = (
    "taskledger.errors",
    "taskledger.api.contexts",
    "taskledger.api.items",
    "taskledger.api.memories",
    "taskledger.api.repos",
    "taskledger.api.runs",
    "taskledger.api.validation",
    "taskledger.api.composition",
    "taskledger.api.runtime_support",
    "taskledger.api.types",
)


@pytest.mark.parametrize("module_name", ALLOWED_MODULES)
def test_allowed_module_is_importable(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None


# ---------------------------------------------------------------------------
# Section 1 – Import boundary (forbidden modules)
# ---------------------------------------------------------------------------

FORBIDDEN_MODULES = (
    "taskledger.storage",
    "taskledger.context",
    "taskledger.compose",
    "taskledger.models",
    "taskledger.models.execution",
    "taskledger.links",
    "taskledger.search",
)


@pytest.mark.parametrize("module_name", FORBIDDEN_MODULES)
def test_forbidden_module_is_not_in_allowed_set(module_name: str) -> None:
    assert module_name not in ALLOWED_MODULES


# ---------------------------------------------------------------------------
# Section 3 – Canonical error imports
# ---------------------------------------------------------------------------

ERROR_NAMES = (
    "TaskledgerError",
    "LaunchError",
    "InvalidPromptError",
    "UnsupportedAgentError",
    "AgentNotInstalledError",
)


@pytest.mark.parametrize("name", ERROR_NAMES)
def test_error_import(name: str) -> None:
    from taskledger import errors

    assert hasattr(errors, name), f"taskledger.errors is missing {name}"
    assert issubclass(getattr(errors, name), Exception)


# ---------------------------------------------------------------------------
# Section 4 – Canonical DTO imports from taskledger.api.types
# ---------------------------------------------------------------------------

DTO_NAMES = (
    "ContextEntry",
    "WorkItem",
    "Memory",
    "Repo",
    "RunRecord",
    "ValidationRecord",
    "ProjectConfig",
    "SourceBudget",
    "ExpandedSelection",
    "ContextSource",
    "ComposedBundle",
    "ExecutionOptions",
    "ExecutionPreviewRecord",
    "ExecutionOutcomeRecord",
    "ExecutionStatus",
)


@pytest.mark.parametrize("name", DTO_NAMES)
def test_dto_import(name: str) -> None:
    from taskledger.api import types

    assert hasattr(types, name), f"taskledger.api.types is missing {name}"


# ---------------------------------------------------------------------------
# Section 5 – Entity API function existence
# ---------------------------------------------------------------------------

ENTITY_CONTRACT: dict[str, tuple[str, ...]] = {
    "taskledger.api.contexts": (
        "save_context",
        "list_contexts",
        "resolve_context",
        "rename_context",
        "delete_context",
    ),
    "taskledger.api.items": (
        "create_item",
        "list_items",
        "show_item",
        "approve_item",
        "reopen_item",
        "close_item",
        "next_action_payload",
    ),
    "taskledger.api.memories": (
        "create_memory",
        "list_memories",
        "resolve_memory",
        "read_memory_body",
        "refresh_memory",
        "rename_memory",
        "write_memory_body",
        "update_memory_body",
        "update_memory_tags",
        "delete_memory",
    ),
    "taskledger.api.repos": (
        "add_repo",
        "list_repos",
        "resolve_repo",
        "resolve_repo_root",
        "set_repo_role",
        "set_default_execution_repo",
        "clear_default_execution_repo",
        "remove_repo",
    ),
    "taskledger.api.runs": (
        "list_runs",
        "show_run",
        "delete_run",
        "cleanup_runs",
        "promote_run_output",
        "promote_run_report",
    ),
    "taskledger.api.validation": (
        "list_validation_records",
        "append_validation_record",
        "remove_validation_records",
    ),
}


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


# ---------------------------------------------------------------------------
# Section 6 – Composition API
# ---------------------------------------------------------------------------

COMPOSITION_NAMES = (
    "SelectionRequest",
    "expand_selection",
    "build_sources",
    "compose_bundle",
    "describe_sources",
    "repo_refs_for_sources",
    "build_compose_payload",
)


@pytest.mark.parametrize("name", COMPOSITION_NAMES)
def test_composition_import(name: str) -> None:
    from taskledger.api import composition

    assert hasattr(composition, name), (
        f"taskledger.api.composition is missing {name}"
    )


def test_old_compose_module_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("taskledger.api.compose")


# ---------------------------------------------------------------------------
# Section 7 – Runtime support API
# ---------------------------------------------------------------------------

RUNTIME_SUPPORT_NAMES = (
    "RunArtifactPaths",
    "get_effective_project_config",
    "create_run_artifact_layout",
    "save_run_record",
    "resolve_repo_root",
)


@pytest.mark.parametrize("name", RUNTIME_SUPPORT_NAMES)
def test_runtime_support_import(name: str) -> None:
    from taskledger.api import runtime_support

    assert hasattr(runtime_support, name), (
        f"taskledger.api.runtime_support is missing {name}"
    )
