from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "taskledger"
MAX_MODULE_LINES = 2000
MAX_FUNCTION_LINES = 250

MODULE_LINE_WHITELIST: dict[str, str] = {
    "taskledger/services/tasks.py": (
        "Temporary compatibility facade while workflow services are extracted."
    ),
}

FUNCTION_LINE_WHITELIST: dict[str, str] = {
    "taskledger/cli_task.py::register_task_v2_commands": (
        "Split command registration into smaller callback modules."
    ),
    "taskledger/cli_plan.py::register_plan_v2_commands": (
        "Split command registration into smaller callback modules."
    ),
    "taskledger/cli_implement.py::register_implement_v2_commands": (
        "Split command registration into smaller callback modules."
    ),
    "taskledger/services/doctor.py::inspect_v2_project": (
        "Extract independent doctor checks into focused inspectors."
    ),
    "taskledger/services/navigation.py::can_perform": (
        "Move action gating decisions into a shared pure decision layer."
    ),
    "taskledger/services/web_dashboard.py::_render_dashboard_css": (
        "Move dashboard CSS into static assets."
    ),
    "taskledger/services/web_dashboard.py::_render_dashboard_script": (
        "Move dashboard JavaScript into static assets."
    ),
}

EXCEPT_EXCEPTION_WHITELIST: dict[str, str] = {
    "taskledger/cli.py:206": (
        "Top-level command dispatch keeps unexpected crashes in structured output."
    ),
    "taskledger/cli.py:455": (
        "Global CLI fallback converts bootstrap failures into LaunchError envelopes."
    ),
    "taskledger/cli_ledger.py:111": (
        "Ledger root fallback degrades gracefully when legacy storage probes fail."
    ),
    "taskledger/cli_ledger.py:464": (
        "Ledger diagnostics command reports unknown failures as structured CLI errors."
    ),
    "taskledger/launcher.py:16": (
        "Launcher wrapper keeps user-facing startup errors consistent."
    ),
    "taskledger/services/doctor.py:97": (
        "Doctor must continue scanning even when one task metadata read fails."
    ),
    "taskledger/services/doctor.py:111": (
        "Doctor must continue scanning even when one plan read fails."
    ),
    "taskledger/services/doctor.py:125": (
        "Doctor must continue scanning even when one todo read fails."
    ),
    "taskledger/services/doctor.py:182": (
        "Doctor storage probe wraps unexpected file decoding failures."
    ),
    "taskledger/services/doctor.py:200": (
        "Doctor lock inspection ignores malformed optional lock metadata."
    ),
    "taskledger/services/doctor.py:460": (
        "Doctor report formatting keeps scan output available when one detail "
        "renderer fails."
    ),
    "taskledger/services/doctor.py:464": (
        "Doctor report formatting keeps scan output available when one warning "
        "renderer fails."
    ),
    "taskledger/services/doctor.py:581": (
        "Doctor JSON rendering converts unknown serialization failures into "
        "diagnostic records."
    ),
    "taskledger/services/doctor.py:614": (
        "Doctor text rendering converts unknown failures into explicit warnings."
    ),
    "taskledger/services/doctor.py:638": (
        "Doctor summary rendering converts unknown failures into explicit warnings."
    ),
    "taskledger/services/tree.py:246": (
        "Tree command keeps partial output when optional metadata parsing fails."
    ),
    "taskledger/services/web_dashboard.py:1512": (
        "Dashboard request handling must keep the server alive on unexpected "
        "route errors."
    ),
    "taskledger/storage/ledger_config.py:85": (
        "Ledger config loader reports parse/runtime differences consistently "
        "across Python versions."
    ),
    "taskledger/storage/migrations.py:267": (
        "Migration scanner continues past one malformed legacy entry."
    ),
    "taskledger/storage/migrations.py:350": (
        "Migration planner emits actionable diagnostics for unknown migration errors."
    ),
    "taskledger/storage/migrations.py:485": (
        "Migration executor records unexpected write failures in audit output."
    ),
    "taskledger/storage/paths.py:138": (
        "Path probe falls back when environment inspection raises platform-"
        "specific errors."
    ),
    "taskledger/storage/project_config.py:184": (
        "Project config loader normalizes parser/runtime exceptions across "
        "Python versions."
    ),
    "taskledger/storage/task_store.py:367": (
        "Task-store metadata fallback keeps reads available when optional front "
        "matter parse fails."
    ),
    "taskledger/storage/task_store.py:885": (
        "Task-store listing tolerates partial decode errors and keeps scanning."
    ),
}


class _FunctionVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self._scope: list[str] = []
        self.lengths: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.end_lineno is not None:
            qualified_name = ".".join([*self._scope, node.name])
            self.lengths[f"{self.rel_path}::{qualified_name}"] = (
                node.end_lineno - node.lineno + 1
            )
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


def _python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_boundary_whitelists_include_reasons() -> None:
    for whitelist in (
        MODULE_LINE_WHITELIST,
        FUNCTION_LINE_WHITELIST,
        EXCEPT_EXCEPTION_WHITELIST,
    ):
        for key, reason in whitelist.items():
            assert key
            assert reason.strip()


def test_service_module_line_budget() -> None:
    module_lines: dict[str, int] = {}
    for path in _python_files():
        rel = _relative(path)
        module_lines[rel] = len(path.read_text(encoding="utf-8").splitlines())

    unexpected = {
        rel: line_count
        for rel, line_count in module_lines.items()
        if line_count > MAX_MODULE_LINES and rel not in MODULE_LINE_WHITELIST
    }
    stale = {
        rel: module_lines.get(rel, 0)
        for rel in MODULE_LINE_WHITELIST
        if module_lines.get(rel, 0) <= MAX_MODULE_LINES
    }

    assert not unexpected, (
        "Modules above line budget without whitelist entry: "
        f"{sorted(unexpected.items())}"
    )
    assert not stale, (
        "Whitelist entries no longer needed for module line budget: "
        f"{sorted(stale.items())}"
    )


def test_service_function_line_budget() -> None:
    long_functions: dict[str, int] = {}
    for path in _python_files():
        rel = _relative(path)
        visitor = _FunctionVisitor(rel)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        long_functions.update(
            {
                name: line_count
                for name, line_count in visitor.lengths.items()
                if line_count > MAX_FUNCTION_LINES
            }
        )

    unexpected = {
        name: line_count
        for name, line_count in long_functions.items()
        if name not in FUNCTION_LINE_WHITELIST
    }
    stale = {
        name: long_functions.get(name, 0)
        for name in FUNCTION_LINE_WHITELIST
        if long_functions.get(name, 0) <= MAX_FUNCTION_LINES
    }

    assert not unexpected, (
        "Functions above line budget without whitelist entry: "
        f"{sorted(unexpected.items())}"
    )
    assert not stale, (
        "Whitelist entries no longer needed for function line budget: "
        f"{sorted(stale.items())}"
    )


def test_except_exception_sites_are_whitelisted() -> None:
    found_sites: set[str] = set()
    for path in _python_files():
        rel = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                found_sites.add(f"{rel}:{node.lineno}")

    expected_sites = set(EXCEPT_EXCEPTION_WHITELIST)
    unexpected = sorted(found_sites - expected_sites)
    stale = sorted(expected_sites - found_sites)

    assert not unexpected, f"Unapproved except Exception sites: {unexpected}"
    assert not stale, f"Whitelist sites no longer present: {stale}"


def test_validation_module_has_no_private_tasks_imports() -> None:
    path = ROOT / "taskledger" / "services" / "validation.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    forbidden: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "taskledger.services.tasks":
            continue
        for alias in node.names:
            if alias.name.startswith("_"):
                forbidden.append(alias.name)

    assert not forbidden, (
        "validation.py must not import private helpers from services.tasks: "
        f"{sorted(forbidden)}"
    )


def test_tasks_validation_gate_wrapper_has_no_local_import_workaround() -> None:
    path = ROOT / "taskledger" / "services" / "tasks.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "_build_validation_gate_report":
                target = node
                break

    assert target is not None, "_build_validation_gate_report not found"
    local_imports = [
        node
        for node in ast.walk(target)
        if isinstance(node, ast.ImportFrom)
        and node.module == "taskledger.services.validation"
    ]
    assert not local_imports, (
        "_build_validation_gate_report should call a top-level imported validation "
        "helper instead of using a local import workaround."
    )


def _function_node(path: Path, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"{name} not found in {path}")


def _assert_wrapper_imports_module(
    path: Path,
    *,
    function_name: str,
    module_name: str,
) -> None:
    target = _function_node(path, function_name)
    local_imports = [
        node
        for node in ast.walk(target)
        if isinstance(node, ast.ImportFrom) and node.module == module_name
    ]
    assert local_imports, (
        f"{function_name} should delegate via local import from {module_name}."
    )


def test_tasks_planning_entrypoints_delegate_to_planning_flow() -> None:
    path = ROOT / "taskledger" / "services" / "tasks.py"
    for function_name in (
        "start_planning",
        "propose_plan",
        "upsert_plan",
        "approve_plan",
    ):
        _assert_wrapper_imports_module(
            path,
            function_name=function_name,
            module_name="taskledger.services.planning_flow",
        )


def test_tasks_implementation_entrypoints_delegate_to_implementation_flow() -> None:
    path = ROOT / "taskledger" / "services" / "tasks.py"
    for function_name in (
        "start_implementation",
        "restart_implementation",
        "resume_implementation",
        "log_implementation",
        "add_implementation_deviation",
        "add_implementation_artifact",
        "run_implementation_command",
        "finish_implementation",
    ):
        _assert_wrapper_imports_module(
            path,
            function_name=function_name,
            module_name="taskledger.services.implementation_flow",
        )


def test_tasks_validation_entrypoints_delegate_to_validation_flow() -> None:
    path = ROOT / "taskledger" / "services" / "tasks.py"
    for function_name in (
        "start_validation",
        "validation_status",
        "add_validation_check",
        "waive_criterion",
        "finish_validation",
    ):
        _assert_wrapper_imports_module(
            path,
            function_name=function_name,
            module_name="taskledger.services.validation_flow",
        )
