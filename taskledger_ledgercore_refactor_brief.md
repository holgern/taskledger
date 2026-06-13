# Taskledger ledgercore usage review and refactoring brief

Generated from reconstructed snapshots:

- `context_taskledger.md` reconstructed into `/mnt/data/reconstructed_taskledger`
- `context_ledgercore.md` reconstructed into `/mnt/data/reconstructed_ledgercore`

Target audience: coding agent implementing the next taskledger refactor.

## Executive verdict

Taskledger already uses ledgercore in the right architectural direction, but only for the first layer of shared primitives.

Current ledgercore usage is concentrated in:

- `taskledger/ids.py`
- `taskledger/refs.py`
- `taskledger/timeutils.py`
- `taskledger/storage/atomic.py`
- `taskledger/storage/common.py`
- `taskledger/storage/frontmatter.py`
- `taskledger/storage/paths.py`
- `taskledger/storage/task_store.py`
- `taskledger/cli_ledger.py`

This is a good start. The main remaining opportunity is to stop hand-rolling YAML, JSON, path, hash, and ID formatting helpers in taskledger when ledgercore already has primitives for them.

Do not move taskledger domain logic into ledgercore. Ledgercore should stay generic: IDs, refs, storage I/O, front matter, path safety, timestamps, and low-level serialization. Taskledger should keep workflow state machines, task lifecycle policy, validation gates, monitor payloads, and CLI semantics.

## Current integration inventory

### Dependency

`pyproject.toml` already declares:

```toml
dependencies = [
    "typer",
    "click",
    "PyYAML",
    "ledgercore>=0.1.0",
    'tomli; python_version < "3.11"',
]
```

Current result: taskledger still imports `yaml` directly in production code, so `PyYAML` remains a direct dependency. After the YAML refactor below, taskledger can likely stop importing PyYAML directly, except where unique-key YAML parsing is intentionally local.

### IDs and refs

Taskledger now has a compatibility facade:

```python
# taskledger/ids.py
from ledgercore.ids import LedgerIdFormat, slugify_ref
from ledgercore.refs import LedgerResourceRef, parse_resource_ref

TASK_ID_FORMAT = LedgerIdFormat(prefix="task", separator="-", width=4)
```

Good:

- `next_project_id()` delegates to `LedgerIdFormat.next()`.
- `slugify_project_ref()` delegates to `ledgercore.ids.slugify_ref()`.
- `normalize_local_resource_id()` delegates to `ledgercore.refs.parse_resource_ref()`.

Taskledger refs are also now backed by ledgercore:

```python
# taskledger/refs.py
from ledgercore.refs import LedgerResourceRef, parse_resource_ref
```

Good:

- Canonical global refs use `tl:task-0001`.
- File-safe aliases use `tl-task-0001`.
- Legacy aliases such as `TL-TASK-0001` still normalize.
- `ledger.code` is correctly separate from the branch-scoped `ledger_ref`.

Important: keep this separation. `ledger_ref` is the branch/local storage namespace (`main`, `feature-a`). `ledger.code` is the stable cross-ledger code (`tl`). Tests currently assert that global refs remain branch-agnostic after `ledger fork`.

### Atomic/text/JSON/front matter

Taskledger has wrapper modules that map ledgercore errors to `LaunchError`:

- `taskledger/storage/atomic.py`
- `taskledger/storage/common.py`
- `taskledger/storage/frontmatter.py`

This is the correct shape. Keep taskledger-facing wrappers so CLI/service code does not need to know ledgercore exception types.

### Timestamp facade

`taskledger/timeutils.py` is now a tiny re-export:

```python
from ledgercore.time import utc_now_iso
```

Good. Keep this compatibility facade unless you are willing to touch many imports.

## Confirmed working subset

I ran:

```bash
PYTHONPATH=/mnt/data/reconstructed_ledgercore:/mnt/data/reconstructed_taskledger \
python -m pytest tests/test_ledgercore_dependency.py tests/test_resource_refs.py -q
```

Result:

```text
8 passed in 0.17s
```

The first run without adding reconstructed ledgercore to `PYTHONPATH` failed with `ModuleNotFoundError: No module named 'ledgercore'`. That is expected in this unpacked analysis environment and does not indicate a package issue when installed normally.

## Main refactoring opportunities

## P0. Centralize YAML through ledgercore

### Problem

Production taskledger still imports `yaml` directly in these modules:

```text
taskledger/cli_changelog.py
taskledger/cli_ledger.py
taskledger/cli_question.py
taskledger/exchange.py
taskledger/services/plan_editing.py
taskledger/services/task_events.py
taskledger/services/tasks.py
taskledger/storage/locks.py
taskledger/storage/meta.py
taskledger/storage/migrations.py
taskledger/storage/task_store.py
```

Some of these are generic YAML object I/O and should use ledgercore. Some are special cases and should stay local for now.

### Add taskledger YAML wrappers

Extend `taskledger/storage/common.py` or create `taskledger/storage/yaml_store.py`.

Recommended: create `taskledger/storage/yaml_store.py` to avoid making `common.py` too broad.

```python
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from ledgercore.errors import YamlStoreError
from ledgercore.yamlio import load_yaml_object as _load_yaml_object
from ledgercore.yamlio import write_yaml as _write_yaml

from taskledger.errors import LaunchError


def load_yaml_object(
    path: Path,
    label: str,
    *,
    missing: Literal["error", "empty"] = "error",
    empty: Literal["error", "empty"] = "empty",
) -> dict[str, object]:
    try:
        return _load_yaml_object(path, label=label, missing=missing, empty=empty)
    except YamlStoreError as exc:
        raise LaunchError(f"Invalid {label} {path}: {exc}") from exc


def write_yaml_object(
    path: Path,
    payload: Mapping[str, object],
    *,
    sort_keys: bool = False,
) -> None:
    try:
        _write_yaml(path, payload, atomic=True, sort_keys=sort_keys)
    except YamlStoreError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc
```

### Replace these immediately

Replace direct `yaml.safe_load()` / `yaml.safe_dump()` in:

1. `taskledger/storage/task_store.py`

Current local duplication:

```python
payload = yaml.safe_load(paths.active_task_path.read_text(encoding="utf-8"))
payload = yaml.safe_load(paths.actor_path.read_text(encoding="utf-8"))
payload = yaml.safe_load(paths.harness_path.read_text(encoding="utf-8"))

def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, yaml.safe_dump(payload, sort_keys=False))
```

Refactor:

```python
from taskledger.storage.yaml_store import load_yaml_object, write_yaml_object

payload = load_yaml_object(paths.active_task_path, "active task state")
...
write_yaml_object(path, payload)
```

2. `taskledger/storage/meta.py`

Current:

```python
payload = yaml.safe_load(path.read_text(encoding="utf-8"))
atomic_write_text(path, yaml.safe_dump(meta.to_dict(), sort_keys=False))
```

Refactor to `load_yaml_object()` / `write_yaml_object()`.

3. `taskledger/cli_changelog.py::_load_batch_entries`

Current:

```python
raw = yaml.safe_load(path.read_text(encoding="utf-8"))
```

Refactor to:

```python
raw = load_yaml_object(path, "batch file")
```

4. `taskledger/cli_ledger.py::ledger_list_command`

Current command does local YAML parsing of `active-task.yaml`.

Better:

- import `ActiveTaskState.from_dict`, or preferably
- use `taskledger.storage.task_store.load_active_task_state()` if the CLI needs only current ledger, or a small storage helper that loads an active state from a specific ledger directory.

Avoid the inline `try: yaml.safe_load(...); except Exception: pass` block. It hides errors too broadly and keeps storage parsing in CLI code.

5. `taskledger/services/task_events.py` and `taskledger/storage/locks.py`

For lock update and task event lock audit writes, use ledgercore YAML dumping where possible.

Caveat: `write_lock()` currently uses `atomic_create_text()` for exclusive lock creation. `ledgercore.yamlio.write_yaml()` always writes/replaces and does not have exclusive-create mode. Keep exclusive create behavior. Either:

- add a small taskledger helper that renders YAML text using PyYAML temporarily, or
- better, add an upstream ledgercore primitive first:

```python
# proposed ledgercore.yamlio
def dumps_yaml_object(payload: Mapping[str, object], *, sort_keys: bool = False) -> str: ...
def atomic_create_yaml(path: Path, payload: Mapping[str, object], *, sort_keys: bool = False) -> None: ...
```

Then taskledger locks can use:

```python
from ledgercore.yamlio import atomic_create_yaml, write_yaml
```

### Keep these local for now

Do not blindly replace these:

1. `taskledger/cli_question.py`

It uses a custom `yaml.SafeLoader` subclass to reject duplicate keys in bulk answer input. `ledgercore.yamlio.load_yaml_object()` does not enforce unique keys. Leave it local unless ledgercore gains `unique_keys=True`.

2. `taskledger/services/tasks.py::_parse_plan_front_matter`

It parses YAML front matter from an in-memory string. Ledgercore currently reads front matter from a file path only. Leave it local or add a ledgercore string parser first.

3. `taskledger/services/plan_editing.py::render_editable_plan`

It renders front matter to a string. Ledgercore currently writes front matter to a path only. Leave it local or add a ledgercore renderer first.

4. `taskledger/storage/migrations.py`

Migration code often needs tolerant legacy parsing. Refactor only after the stable storage path is cleaned up.

### Acceptance criteria for P0

- Direct production `import yaml` count should drop sharply.
- Allowed remaining direct YAML users should be documented in a test whitelist:
  - `taskledger/cli_question.py`
  - `taskledger/services/tasks.py` until ledgercore has string front matter parsing
  - `taskledger/services/plan_editing.py` until ledgercore has string front matter rendering
  - `taskledger/storage/migrations.py` if legacy migration tolerance is still needed
- Existing tests for locks, active actor/harness state, changelog batch import, and v2 CLI must pass.
- Add tests for `taskledger.storage.yaml_store` error translation.

## P1. Route JSON index reads through ledgercore

### Problem

`taskledger/storage/common.py` already wraps `ledgercore.jsonio`, but some index modules still use direct `json.loads()`:

- `taskledger/storage/task_index.py::_read_index`
- `taskledger/storage/sidecar_index.py`
- some NDJSON append/load paths in `storage/events.py` and `storage/agent_logs.py`

For normal JSON object files, use ledgercore. For NDJSON, ledgercore currently has no helper.

### Refactor object indexes

Add a tolerant helper for derived indexes:

```python
# taskledger/storage/common.py or taskledger/storage/json_store.py
def try_load_json_object(path: Path, label: str) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return _load_json_object(path, label=label, missing="error", empty="empty")
    except JsonStoreError:
        return None
```

Use it in:

```python
# taskledger/storage/task_index.py
index = try_load_json_object(_task_index_path(paths), "task index")
```

And in `sidecar_index.py`.

Preserve current derived-index behavior:

- missing index => rebuild
- malformed index => rebuild
- stale entries => refresh or rebuild
- do not make malformed derived index a hard migration blocker

### Do not refactor NDJSON yet

`taskledger/storage/events.py` and `taskledger/storage/agent_logs.py` append and scan newline-delimited JSON. Ledgercore currently has `jsonio.py` for whole JSON files, not NDJSON.

Options:

- leave NDJSON local, or
- add `ledgercore.ndjson` with:
  - `append_ndjson(path, payload)`
  - `iter_ndjson_objects(paths)`
  - `load_ndjson_objects(path, skip_invalid=False)`

Only move NDJSON after ledgercore has this primitive.

## P1. Normalize ID usage through the taskledger facade

### Problem

Some code still imports `LedgerIdFormat` directly from ledgercore outside `taskledger/ids.py`:

```text
taskledger/cli_ledger.py
taskledger/storage/task_store.py
```

This weakens the facade. It also repeats format construction.

### Refactor

Extend `taskledger/ids.py`:

```python
TASK_ID_FORMAT = LedgerIdFormat(prefix="task", separator="-", width=4)

def format_task_id(number: int) -> str:
    return TASK_ID_FORMAT.format(number)

def normalize_numeric_ref(ref: str, prefix: str) -> str:
    fmt = LedgerIdFormat(prefix=prefix, separator="-", width=4)
    try:
        parts = fmt.parse_parts(ref)
    except ValueError:
        return ref
    return fmt.format(parts.number)

def numeric_id_sort_key(value: str, *, prefix: str) -> tuple[int, str]:
    fmt = LedgerIdFormat(prefix=prefix, separator="-", width=4)
    try:
        return (fmt.parse_parts(value).number, value)
    except ValueError:
        return (10**9, value)
```

Then replace:

- `taskledger/cli_ledger.py` direct import of `ledgercore.ids.LedgerIdFormat`
- `taskledger/storage/task_store.py::_normalize_numeric_ref`
- `taskledger/storage/task_store.py::task_numeric_sort_key`

Recommended import policy:

- Application/service/CLI code imports `taskledger.ids`.
- `taskledger.ids` imports ledgercore.
- `taskledger.refs` imports ledgercore.
- Storage wrappers import ledgercore.
- Avoid direct ledgercore imports elsewhere unless there is a clear low-level reason.

### Optional architecture test

Add a test that fails on direct `ledgercore` imports outside an allowlist:

```text
taskledger/ids.py
taskledger/refs.py
taskledger/timeutils.py
taskledger/storage/*.py
```

Allow `taskledger/cli_ledger.py` only temporarily if needed. The goal is not to hide ledgercore; the goal is to prevent service/CLI code from depending on ledgercore exception semantics.

## P1. Consolidate path safety and relative path helpers

### Current state

Taskledger uses ledgercore only for config discovery:

```python
from ledgercore.paths import find_config_upwards
```

Ledgercore also provides:

- `validate_relative_posix_path()`
- `resolve_relative_child()`
- `resolve_config_relative_path()`
- `is_relative_to()`
- `locate_config()`

Taskledger still has many local path safety checks.

### Refactor targets

1. `taskledger/exchange.py`

Current archive restore checks manually inspect path traversal:

```python
relative = Path(member_name[len(ARTIFACTS_PREFIX):])
if relative.is_absolute() or ".." in relative.parts:
    ...
destination = paths.project_dir / relative
```

Use ledgercore path validation:

```python
from ledgercore.paths import resolve_relative_child, PathValidationError

destination = resolve_relative_child(
    paths.project_dir,
    relative.as_posix(),
    field_name="artifact path",
)
```

Wrap `PathValidationError` as `LaunchError`.

2. `taskledger/services/git_sync.py`

Config-relative paths such as sync repo and project path should use:

```python
resolve_config_relative_path(config_path, value, field_name="sync.git.repo")
```

If taskledger intentionally supports environment variable expansion, keep a thin wrapper that expands variables first and then calls ledgercore validation.

3. `taskledger/services/storage_locations.py`

This module appears to reimplement config-relative path handling. Use `resolve_config_relative_path()` where compatible.

4. `taskledger/services/plan_editing.py::_resolve_candidate`

Use `ledgercore.paths.is_relative_to()` for containment checks to avoid repeated `candidate == root or root in candidate.parents`.

5. `taskledger/storage/common.py`

Current helpers:

```python
def relative_to_project(paths: ProjectPaths, target: Path) -> str: ...
def relative_to_workspace(paths: ProjectPaths, target: Path) -> str: ...
```

Consider adding a generic safe formatter:

```python
def relative_label(root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return target.as_posix()
```

Then replace `_path_label()` in `task_store.py`, `_relative_path()` variants in doctor/reporting code, and ad hoc `try: relative_to(...)` blocks.

## P1. Use ledgercore content hashing where it fits

### Current state

Direct `hashlib.sha256` appears in:

- `taskledger/api/handoff.py`
- `taskledger/services/file_links.py`
- `taskledger/services/navigation.py`
- `taskledger/services/next_action_payload.py`
- `taskledger/services/plan_hash.py`
- `taskledger/storage/task_store.py`

Ledgercore already has:

```python
ledgercore.io.content_hash(text: str) -> str
```

### Refactor safe cases

Use `content_hash()` for string hashes:

```python
from ledgercore.io import content_hash

context_hash = f"sha256:{content_hash(context_body)}"
```

Good targets:

- `taskledger/api/handoff.py`
- `taskledger/services/next_action_payload.py`
- `taskledger/services/navigation.py`
- `taskledger/services/plan_hash.py`
- `taskledger/storage/task_store.py::_link_id_from_path`

Keep `taskledger/services/file_links.py::_sha256_file()` local for now because ledgercore does not have a streaming file hash helper.

Better upstream ledgercore addition:

```python
def file_content_hash(path: Path, *, algorithm: str = "sha256", prefix: bool = False) -> str: ...
def prefixed_content_hash(text: str, *, algorithm: str = "sha256") -> str: ...
```

Then taskledger can standardize on `sha256:<hex>` where required.

## P1. Clean up storage layout duplication

### Problem

Taskledger now has two overlapping path containers:

- `taskledger/storage/paths.py::ProjectPaths`
- `taskledger/storage/task_store.py::V2Paths`

`ProjectPaths.project_dir` is actually the current ledger directory in v2. `V2Paths` then adds both `ledger_dir` and `project_dir` as an alias. This makes future changes risky.

### Recommended refactor

Introduce one canonical taskledger layout dataclass, probably in `taskledger/storage/layout.py`:

```python
@dataclass(slots=True, frozen=True)
class TaskledgerLayout:
    workspace_root: Path
    config_path: Path
    taskledger_root: Path
    ledger_ref: str
    ledger_dir: Path
    repos_dir: Path
    indexes_dir: Path
    tasks_dir: Path
    releases_dir: Path
    ...
```

Then:

- keep `ProjectPaths` and `V2Paths` as compatibility aliases during one refactor step, or
- remove them if no migration compatibility is needed.

Use ledgercore only for generic path operations. The layout itself is taskledger-specific and should remain in taskledger unless ledgercore grows a generic `LedgerLayout` primitive.

### Important bug-risk note

`taskledger/storage/init.py::_ensure_additive_project_files()` still creates some unscoped paths under `paths.taskledger_dir / "tasks"`, `"intros"`, `"events"`, `"indexes"` even though the current v2 layout uses `.taskledger/ledgers/<ref>/...`.

Review this while consolidating layout. It may be a stale compatibility behavior, but it should not silently reintroduce unscoped ledger directories if the product goal is isolated ledgers.

## P2. Push missing generic primitives into ledgercore

Some remaining duplication cannot be eliminated cleanly without extending ledgercore first.

Recommended ledgercore additions:

### 1. YAML text rendering and exclusive create

Needed by taskledger locks and audit records.

```python
def dumps_yaml_object(payload: Mapping[str, object], *, sort_keys: bool = False) -> str: ...

def atomic_create_yaml(
    path: Path,
    payload: Mapping[str, object],
    *,
    sort_keys: bool = False,
    fsync: bool = True,
    fast_io_env_var: str | None = None,
) -> None: ...
```

### 2. String front matter parser/renderer

Needed by editable plan handling and CLI input parsing.

```python
def parse_front_matter_text(text: str) -> tuple[dict[str, object], str]: ...

def render_front_matter_document(
    metadata: Mapping[str, object],
    body: str,
    *,
    body_mode: BodyMode = "preserve",
) -> str: ...
```

`write_front_matter_document()` should call `render_front_matter_document()` internally.

### 3. NDJSON helpers

Needed by action/event logs and agent command logs.

```python
def append_ndjson_object(path: Path, payload: Mapping[str, object]) -> None: ...

def load_ndjson_objects(path: Path, *, label: str = "NDJSON log") -> list[dict[str, object]]: ...

def iter_ndjson_objects(paths: Iterable[Path], *, skip_invalid: bool = False) -> Iterator[dict[str, object]]: ...
```

### 4. TOML object loader

Taskledger currently has repeated `tomllib` loading in:

- `taskledger/storage/ledger_config.py`
- `taskledger/storage/project_config.py`
- `taskledger/storage/project_identity.py`

Ledgercore does not currently provide `tomlio.py`.

Add to ledgercore:

```python
def load_toml_object(
    path: Path,
    *,
    label: str = "TOML document",
    missing: Literal["error", "empty"] = "error",
    empty: Literal["error", "empty"] = "empty",
) -> dict[str, object]: ...
```

Taskledger can still keep comment-preserving TOML patch logic locally. Generic parse/load belongs in ledgercore; taskledger-specific key validation and patch placement does not.

### 5. Hash helpers

```python
def prefixed_content_hash(text: str, *, algorithm: str = "sha256") -> str: ...
def file_content_hash(path: Path, *, algorithm: str = "sha256", prefix: bool = False) -> str: ...
```

## What not to move to ledgercore

Keep these in taskledger:

- task states and lifecycle policy
- active task semantics
- actor/harness resolution
- lock ownership semantics
- task/todo/plan/question/check/review/changelog domain models
- monitor/dashboard/usage read models
- CLI command contracts
- release/changelog categories
- worker pipeline behavior
- task archive/import policy, except low-level path/JSON/YAML helpers

Ledgercore should not know what a task, plan, acceptance criterion, or validation gate is.

## Suggested implementation sequence

### Step 1: Add `taskledger.storage.yaml_store`

Add wrapper tests:

```text
tests/test_storage_yaml_store.py
```

Test cases:

- missing file with `missing="empty"` returns `{}`
- missing file with `missing="error"` raises `LaunchError`
- non-mapping YAML raises `LaunchError`
- write preserves deterministic YAML and final newline
- write creates parent directories

### Step 2: Replace simple YAML object reads/writes

Targets:

```text
taskledger/storage/task_store.py
taskledger/storage/meta.py
taskledger/cli_changelog.py
```

Run:

```bash
pytest tests/test_actor_harness_state.py \
       tests/test_project_root_config.py \
       tests/test_changelog_entries.py \
       tests/test_changelog_build.py \
       tests/test_taskledger_v2_cli.py
```

### Step 3: Handle locks carefully

Do not break exclusive create semantics.

Either:

- keep `atomic_create_text()` plus a local YAML dump helper for now, or
- first implement `ledgercore.yamlio.atomic_create_yaml()` and then update taskledger.

Run:

```bash
pytest tests/test_locks_audit.py \
       tests/test_next_action_expired_lock.py \
       tests/test_active_task.py \
       tests/test_agent_session_protocol.py
```

### Step 4: Move JSON object index reads to wrapper

Targets:

```text
taskledger/storage/task_index.py
taskledger/storage/sidecar_index.py
```

Run:

```bash
pytest tests/test_performance_caching.py \
       tests/test_sidecar_collections.py \
       tests/test_monitor.py \
       tests/test_ready_work.py
```

### Step 5: Normalize ID facade usage

Targets:

```text
taskledger/ids.py
taskledger/cli_ledger.py
taskledger/storage/task_store.py
```

Run:

```bash
pytest tests/test_ledgercore_dependency.py \
       tests/test_resource_refs.py \
       tests/test_taskledger_branch_scoped_ledgers.py \
       tests/test_taskledger_v2_cli.py
```

### Step 6: Add boundary tests

Add one or both:

1. Direct ledgercore import allowlist.
2. Direct production `import yaml` allowlist.

This prevents slow drift back to local implementations.

## Concrete review findings

### Good existing decisions

1. `taskledger/ids.py` is the right compatibility facade.
2. `taskledger/refs.py` cleanly maps ledgercore `IdFormatError` to taskledger `LaunchError`.
3. `taskledger/storage/atomic.py` correctly keeps taskledger’s fast test I/O environment variable while delegating the atomic operation.
4. `taskledger/storage/frontmatter.py` is a good wrapper: it keeps taskledger error wording while using ledgercore parsing/writing.
5. `ledger.code` and `ledger_ref` are correctly distinct.

### Refactoring smells

1. CLI code parses storage YAML in `cli_ledger.py`.
2. `task_store.py` imports `yaml` and contains generic `_write_yaml()`.
3. `task_index.py` and `sidecar_index.py` still use direct `json.loads()` despite `storage/common.py` already wrapping ledgercore JSON.
4. Direct `LedgerIdFormat` use in `cli_ledger.py` and `task_store.py` bypasses the facade.
5. Multiple path-label helpers repeat `try: relative_to(...)`.
6. Layout naming is confusing: `ProjectPaths.project_dir` is a ledger directory in v2.

## Expected end state

After the refactor:

- `taskledger` depends on ledgercore for all generic storage/ID/ref primitives.
- Production direct `import yaml` is reduced to documented exceptions only.
- Production direct `json.loads()` is limited to NDJSON until ledgercore has NDJSON helpers.
- Direct `ledgercore` imports outside storage/ID/ref/time facades are either gone or explicitly whitelisted.
- Taskledger storage code is smaller and more consistent.
- The branch-scoped ledger model remains unchanged.
- Cross-ledger refs stay canonical as `<ledger>:<kind>-<number>`, for example `tl:task-0001`.
