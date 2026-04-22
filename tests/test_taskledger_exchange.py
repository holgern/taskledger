from __future__ import annotations

import json
from pathlib import Path

from taskledger.api.contexts import save_context
from taskledger.api.items import create_item
from taskledger.api.memories import create_memory, read_memory_body
from taskledger.api.project import (
    init_project,
    project_export,
    project_import,
    project_snapshot,
)
from taskledger.api.validation import append_validation_record


def test_project_export_import_and_snapshot_round_trip(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    snapshot_root = tmp_path / "snapshots"
    source_root.mkdir()
    destination_root.mkdir()
    snapshot_root.mkdir()

    init_project(source_root)
    init_project(destination_root)
    analysis = create_memory(source_root, name="Analysis", body="Current state")
    validation = create_memory(source_root, name="Validation", body="Checks passed")
    item = create_item(source_root, slug="parser-fix", description="Repair parser")
    save_context(
        source_root,
        name="Parser Context",
        memory_refs=(analysis.id,),
        item_refs=(item.id,),
    )
    append_validation_record(
        source_root,
        project_item_ref=item.id,
        memory_ref=validation.id,
        kind="smoke",
        status="passed",
        verdict="ok",
    )

    exported = project_export(source_root, include_bodies=True)
    imported_payload = project_import(
        destination_root,
        text=json.dumps(exported),
        replace=True,
    )
    snapshot_payload = project_snapshot(
        source_root,
        output_dir=snapshot_root,
        include_bodies=True,
    )

    assert exported["counts"]["memories"] == 2
    assert imported_payload["counts"]["memories"] == 2
    assert imported_payload["counts"]["contexts"] == 1
    assert imported_payload["counts"]["validation_records"] == 1
    assert read_memory_body(destination_root, analysis.id) == "Current state"
    snapshot_dir = Path(snapshot_payload["snapshot_dir"])
    assert snapshot_dir.exists()
    assert (snapshot_dir / "project-export.json").exists()
