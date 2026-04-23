from __future__ import annotations

from pathlib import Path

from taskledger.models import ItemStageRecord
from taskledger.storage import init_project_state, resolve_project_paths
from taskledger.storage.stages import (
    append_stage_record,
    item_stage_records,
    latest_stage_record,
    load_stage_records,
    replace_stage_record,
    save_stage_records,
)


def _paths(tmp_path: Path):
    init_project_state(tmp_path)
    return resolve_project_paths(tmp_path)


def _record(
    item_ref: str = "it-1",
    stage_id: str = "implement",
    record_id: str = "sr-1",
    workflow_id: str = "wf-1",
    status: str = "running",
    created_at: str | None = "2025-01-01T00:00:00",
    updated_at: str | None = None,
) -> ItemStageRecord:
    return ItemStageRecord(
        record_id=record_id,
        item_ref=item_ref,
        workflow_id=workflow_id,
        stage_id=stage_id,
        status=status,
        origin=None,
        requested_by=None,
        run_id=None,
        created_at=created_at,
        updated_at=updated_at,
    )


class TestLoadAndSaveStageRecords:
    def test_load_empty(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        assert load_stage_records(paths) == []

    def test_save_and_reload_round_trip(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        record = _record()
        save_stage_records(paths, [record])
        loaded = load_stage_records(paths)
        assert len(loaded) == 1
        assert loaded[0].record_id == "sr-1"
        assert loaded[0].item_ref == "it-1"

    def test_append_adds_to_existing(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [_record(record_id="sr-1")])
        appended = append_stage_record(paths, _record(record_id="sr-2"))
        assert appended.record_id == "sr-2"
        assert len(load_stage_records(paths)) == 2


class TestItemStageRecords:
    def test_filters_by_item_ref(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [
            _record(item_ref="it-1", record_id="sr-1"),
            _record(item_ref="it-2", record_id="sr-2"),
            _record(item_ref="it-1", record_id="sr-3"),
        ])
        result = item_stage_records(paths, "it-1")
        assert [r.record_id for r in result] == ["sr-1", "sr-3"]

    def test_returns_empty_for_no_match(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [_record(item_ref="it-1")])
        assert item_stage_records(paths, "it-99") == []


class TestLatestStageRecord:
    def test_returns_none_when_no_records(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        assert latest_stage_record(paths, "it-1", "implement") is None

    def test_returns_none_when_stage_id_mismatch(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [_record(stage_id="plan")])
        assert latest_stage_record(paths, "it-1", "implement") is None

    def test_returns_none_when_item_ref_mismatch(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [_record(item_ref="it-1")])
        assert latest_stage_record(paths, "it-99", "implement") is None

    def test_picks_latest_by_updated_at(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [
            _record(record_id="sr-1", updated_at="2025-01-01T00:00:00"),
            _record(record_id="sr-2", updated_at="2025-01-02T00:00:00"),
        ])
        result = latest_stage_record(paths, "it-1", "implement")
        assert result is not None
        assert result.record_id == "sr-2"

    def test_picks_latest_by_created_at_when_updated_at_equal(
        self, tmp_path: Path
    ) -> None:
        paths = _paths(tmp_path)
        save_stage_records(
            paths,
            [
                _record(
                    record_id="sr-1",
                    created_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00",
                ),
                _record(
                    record_id="sr-2",
                    created_at="2025-01-02T00:00:00",
                    updated_at="2025-01-01T00:00:00",
                ),
            ],
        )
        result = latest_stage_record(paths, "it-1", "implement")
        assert result is not None
        assert result.record_id == "sr-2"

    def test_picks_latest_by_record_id_when_timestamps_equal(
        self, tmp_path: Path
    ) -> None:
        paths = _paths(tmp_path)
        save_stage_records(
            paths,
            [
                _record(
                    record_id="sr-1",
                    created_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00",
                ),
                _record(
                    record_id="sr-2",
                    created_at="2025-01-01T00:00:00",
                    updated_at="2025-01-01T00:00:00",
                ),
            ],
        )
        result = latest_stage_record(paths, "it-1", "implement")
        assert result is not None
        assert result.record_id == "sr-2"


class TestReplaceStageRecord:
    def test_replaces_matching_record(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        original = _record(record_id="sr-1", status="running")
        save_stage_records(paths, [original])

        updated = _record(record_id="sr-1", status="succeeded")
        returned = replace_stage_record(paths, updated)

        assert returned.status == "succeeded"
        loaded = load_stage_records(paths)
        assert len(loaded) == 1
        assert loaded[0].status == "succeeded"

    def test_raises_on_unknown_record_id(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        save_stage_records(paths, [_record(record_id="sr-1")])

        try:
            replace_stage_record(paths, _record(record_id="sr-99"))
        except Exception as exc:
            assert "Unknown stage record" in str(exc)
        else:
            raise AssertionError("expected LaunchError for unknown record_id")
