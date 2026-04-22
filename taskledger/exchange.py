from __future__ import annotations

import json
import shutil
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.models import (
    ItemStageRecord,
    ProjectContextEntry,
    ProjectMemory,
    ProjectRepo,
    ProjectRunRecord,
    ProjectWorkItem,
    WorkflowDefinition,
    utc_now_iso,
)
from taskledger.storage import (
    ensure_project_exists,
    load_project_state,
    load_run_records,
    load_stage_records,
    load_validation_records,
    load_workflow_definitions,
    save_contexts,
    save_memories,
    save_repos,
    save_run_record,
    save_stage_records,
    save_validation_records,
    save_work_items,
    save_workflow_definitions,
)


def export_project_payload(
    workspace_root: Path,
    *,
    include_bodies: bool = False,
    include_run_artifacts: bool = False,
) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=None)
    runs = load_run_records(state.paths, limit=None)
    payload: dict[str, object] = {
        "kind": "project_export",
        "version": 1,
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "project_dir": str(state.paths.project_dir),
        "config_overrides": dict(state.config_overrides),
        "config_text": state.paths.config_path.read_text(encoding="utf-8"),
        "repos": [item.to_dict() for item in state.repos],
        "memories": [item.to_dict() for item in state.memories],
        "contexts": [item.to_dict() for item in state.contexts],
        "work_items": [item.to_dict() for item in state.work_items],
        "workflows": [
            item.to_dict() for item in load_workflow_definitions(state.paths)
        ],
        "stage_records": [item.to_dict() for item in load_stage_records(state.paths)],
        "runs": [item.to_dict() for item in runs],
        "validation_records": load_validation_records(state.paths),
        "options": {
            "include_bodies": include_bodies,
            "include_run_artifacts": include_run_artifacts,
        },
        "counts": {
            "repos": len(state.repos),
            "memories": len(state.memories),
            "contexts": len(state.contexts),
            "work_items": len(state.work_items),
            "workflows": len(load_workflow_definitions(state.paths)),
            "stage_records": len(load_stage_records(state.paths)),
            "runs": len(runs),
            "validation_records": len(load_validation_records(state.paths)),
        },
    }
    if include_bodies:
        payload["memory_bodies"] = {
            item.id: (state.paths.project_dir / item.path).read_text(encoding="utf-8")
            for item in state.memories
            if (state.paths.project_dir / item.path).exists()
        }
        payload["context_payloads"] = {
            item.id: json.loads(
                (state.paths.project_dir / item.path).read_text(encoding="utf-8")
            )
            for item in state.contexts
            if (state.paths.project_dir / item.path).exists()
        }
    if include_run_artifacts:
        payload["run_artifacts"] = _collect_run_artifacts(state.paths.runs_dir, runs)
    return payload


def parse_project_import_payload(text: str, *, format_name: str) -> dict[str, object]:
    if format_name != "json":
        raise LaunchError(f"Unsupported project import format: {format_name}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Invalid project import JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchError("Project import JSON must be an object.")
    if payload.get("kind") not in {None, "project_export"}:
        raise LaunchError("Unsupported project import payload kind.")
    return payload


def import_project_payload(
    workspace_root: Path,
    *,
    payload: dict[str, object],
    replace: bool,
) -> dict[str, object]:
    paths = ensure_project_exists(workspace_root)
    _write_project_config(paths, payload)

    imported_repos = _objects_from_payload(payload, "repos", ProjectRepo.from_dict)
    imported_memories = _objects_from_payload(
        payload, "memories", ProjectMemory.from_dict
    )
    imported_contexts = _objects_from_payload(
        payload, "contexts", ProjectContextEntry.from_dict
    )
    imported_work_items = _objects_from_payload(
        payload,
        "work_items",
        ProjectWorkItem.from_dict,
    )
    imported_workflows = _objects_from_payload(
        payload,
        "workflows",
        WorkflowDefinition.from_dict,
    )
    imported_stage_records = _objects_from_payload(
        payload,
        "stage_records",
        ItemStageRecord.from_dict,
    )
    imported_runs = _objects_from_payload(payload, "runs", ProjectRunRecord.from_dict)
    imported_validation_records = _dict_list(payload.get("validation_records"))

    if replace:
        save_repos(paths, imported_repos)
        save_memories(paths, imported_memories)
        save_contexts(paths, imported_contexts)
        save_work_items(paths, imported_work_items)
        save_workflow_definitions(paths, imported_workflows)
        save_stage_records(paths, imported_stage_records)
        save_validation_records(paths, imported_validation_records)
    else:
        state = load_project_state(workspace_root, recent_runs_limit=None)
        save_repos(paths, _merge_named(state.repos, imported_repos, key="slug"))
        save_memories(paths, _merge_named(state.memories, imported_memories, key="id"))
        save_contexts(
            paths, _merge_named(state.contexts, imported_contexts, key="id")
        )
        save_work_items(
            paths,
            _merge_named(state.work_items, imported_work_items, key="id"),
        )
        save_workflow_definitions(
            paths,
            _merge_named(
                load_workflow_definitions(paths),
                imported_workflows,
                key="workflow_id",
            ),
        )
        save_stage_records(
            paths,
            _merge_named(
                load_stage_records(paths),
                imported_stage_records,
                key="record_id",
            ),
        )
        current_records = load_validation_records(paths)
        merged_records = _merge_dict_items(
            current_records,
            imported_validation_records,
            key="id",
        )
        save_validation_records(paths, merged_records)

    _write_memory_bodies(paths, payload, imported_memories)
    _materialize_runs(paths, payload, imported_runs, replace=replace)

    refreshed = load_project_state(workspace_root, recent_runs_limit=None)
    return {
        "kind": "project_import",
        "replace": replace,
        "counts": {
            "repos": len(refreshed.repos),
            "memories": len(refreshed.memories),
            "contexts": len(refreshed.contexts),
            "work_items": len(refreshed.work_items),
            "workflows": len(load_workflow_definitions(refreshed.paths)),
            "stage_records": len(load_stage_records(refreshed.paths)),
            "runs": len(load_run_records(refreshed.paths, limit=None)),
            "validation_records": len(load_validation_records(refreshed.paths)),
        },
    }


def write_project_snapshot(
    workspace_root: Path,
    *,
    output_dir: Path,
    include_bodies: bool,
    include_run_artifacts: bool,
) -> dict[str, object]:
    payload = export_project_payload(
        workspace_root,
        include_bodies=include_bodies,
        include_run_artifacts=include_run_artifacts,
    )
    timestamp = utc_now_iso().replace(":", "-").replace("+00:00", "Z")
    snapshot_dir = output_dir / f"project-snapshot-{timestamp}"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    export_path = snapshot_dir / "project-export.json"
    export_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "kind": "project_snapshot",
        "snapshot_dir": str(snapshot_dir),
        "export_path": str(export_path),
        "include_bodies": include_bodies,
        "include_run_artifacts": include_run_artifacts,
    }


def _objects_from_payload(payload, key, parser):
    items = _dict_list(payload.get(key))
    return [parser(item) for item in items]


def _dict_list(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise LaunchError("Expected list payload value.")
    output: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            output.append(item)
    return output


def _merge_named(existing, incoming, *, key: str):
    merged = {getattr(item, key): item for item in existing}
    for item in incoming:
        merged[getattr(item, key)] = item
    return sorted(merged.values(), key=lambda item: str(getattr(item, key)))


def _merge_dict_items(existing, incoming, *, key: str):
    merged = {str(item.get(key, "")): item for item in existing}
    for item in incoming:
        merged[str(item.get(key, ""))] = item
    values: list[dict[str, object]] = []
    for item_key, value in sorted(merged.items(), key=lambda pair: pair[0]):
        if not item_key:
            continue
        values.append(value)
    return values


def _write_project_config(paths, payload: dict[str, object]) -> None:
    config_text = payload.get("config_text")
    if isinstance(config_text, str):
        paths.config_path.write_text(config_text, encoding="utf-8")


def _write_memory_bodies(paths, payload: dict[str, object], imported_memories):
    body_map = payload.get("memory_bodies")
    memory_bodies = body_map if isinstance(body_map, dict) else {}
    for memory in imported_memories:
        body_path = paths.project_dir / memory.path
        body = memory_bodies.get(memory.id)
        if isinstance(body, str) and body.strip():
            body_path.parent.mkdir(parents=True, exist_ok=True)
            body_path.write_text(body, encoding="utf-8")
            continue
        if body_path.exists():
            body_path.unlink()


def _materialize_runs(
    paths,
    payload: dict[str, object],
    imported_runs,
    *,
    replace: bool,
) -> None:
    run_artifacts = payload.get("run_artifacts")
    artifacts_map = run_artifacts if isinstance(run_artifacts, dict) else {}
    if replace:
        if paths.runs_dir.exists():
            shutil.rmtree(paths.runs_dir)
        paths.runs_dir.mkdir(parents=True, exist_ok=True)
    for record in imported_runs:
        _validate_run_id(record.run_id)
        run_dir = paths.runs_dir / record.run_id
        if run_dir.exists() and replace:
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        save_run_record(run_dir, record)
        files = artifacts_map.get(record.run_id)
        if not isinstance(files, dict):
            continue
        for relative, content in files.items():
            if not isinstance(relative, str) or not isinstance(content, str):
                continue
            target = (run_dir / relative).resolve()
            try:
                target.relative_to(run_dir.resolve())
            except ValueError as exc:
                raise LaunchError(f"Invalid run artifact path: {relative}") from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")


def _collect_run_artifacts(
    runs_dir: Path,
    records: list[ProjectRunRecord],
) -> dict[str, dict[str, str]]:
    collected: dict[str, dict[str, str]] = {}
    for record in records:
        run_dir = runs_dir / record.run_id
        if not run_dir.exists() or not run_dir.is_dir():
            continue
        files: dict[str, str] = {}
        for path in run_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(run_dir))
            if relative == "record.json":
                continue
            try:
                files[relative] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        if files:
            collected[record.run_id] = files
    return collected


def _validate_run_id(run_id: str) -> None:
    if not run_id or "/" in run_id or ".." in run_id:
        raise LaunchError(f"Invalid run id in import payload: {run_id}")
