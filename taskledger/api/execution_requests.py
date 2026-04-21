from __future__ import annotations

from pathlib import Path

from taskledger.api.composition import (
    SelectionRequest,
    build_compose_payload,
    build_sources,
    compose_bundle,
    expand_selection,
    repo_refs_for_sources,
)
from taskledger.api.runtime_support import get_effective_project_config
from taskledger.api.types import (
    ExecutionOptions,
    ExecutionOutcomeRecord,
    ExecutionRequest,
    ExpandedExecutionRequest,
    SourceBudget,
)
from taskledger.api.workflows import (
    mark_stage_failed,
    mark_stage_succeeded,
)
from taskledger.storage import load_project_state, resolve_work_item
from taskledger.workflow import (
    build_execution_request_for_item,
    build_expanded_execution_request,
    execution_outcome_summary,
)


def build_execution_request(
    workspace_root: Path,
    *,
    item_ref: str,
    stage_id: str,
    prompt: str | None = None,
    repo_refs: tuple[str, ...] = (),
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
    run_in_repo: str | None = None,
    save_target: str | None = None,
    save_mode: str | None = None,
) -> ExecutionRequest:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    selection = expand_selection(
        workspace_root,
        SelectionRequest(
            memory_refs=memory_refs,
            file_refs=file_refs,
            item_refs=item_refs,
            inline_texts=inline_texts,
            loop_latest_refs=loop_latest_refs,
        ),
    )
    request = build_execution_request_for_item(
        state,
        item,
        stage_id=stage_id,
        context_inputs=(),
        memory_inputs=selection.memory_inputs,
        file_inputs=selection.file_inputs,
        item_inputs=selection.item_inputs,
        inline_inputs=selection.inline_inputs,
        loop_artifact_inputs=selection.loop_artifact_inputs,
        prompt_seed=prompt,
        run_in_repo=run_in_repo
        or item.target_repo_ref
        or (repo_refs[0] if repo_refs else None),
        save_mode=save_mode,
    )
    if save_target is not None:
        request = ExecutionRequest(
            request_id=request.request_id,
            item_ref=request.item_ref,
            workflow_id=request.workflow_id,
            stage_id=request.stage_id,
            context_inputs=request.context_inputs,
            memory_inputs=request.memory_inputs,
            file_inputs=request.file_inputs,
            item_inputs=request.item_inputs,
            inline_inputs=request.inline_inputs,
            loop_artifact_inputs=request.loop_artifact_inputs,
            instruction_template_id=request.instruction_template_id,
            prompt_seed=request.prompt_seed,
            run_in_repo=request.run_in_repo,
            save_target=save_target,
            save_mode=request.save_mode,
            metadata=request.metadata,
        )
    return request


def expand_execution_request(
    workspace_root: Path,
    *,
    request: ExecutionRequest,
    options: ExecutionOptions | None = None,
) -> ExpandedExecutionRequest:
    config = get_effective_project_config(workspace_root)
    source_budget = SourceBudget(
        max_source_chars=config.default_source_max_chars,
        max_total_chars=config.default_total_source_max_chars,
        head_lines=config.default_source_head_lines,
        tail_lines=config.default_source_tail_lines,
    )
    sources = build_sources(
        workspace_root,
        selection=_selection_from_request(request),
        default_context_order=config.default_context_order,
        source_budget=source_budget,
    )
    prompt = request.prompt_seed or ""
    bundle = compose_bundle(prompt=prompt, sources=sources)
    payload = build_compose_payload(
        context_name=None,
        prompt=prompt,
        explicit_inputs={
            "context_inputs": request.context_inputs,
            "memory_inputs": request.memory_inputs,
            "file_inputs": request.file_inputs,
            "item_inputs": request.item_inputs,
            "inline_inputs": request.inline_inputs,
            "loop_artifact_inputs": request.loop_artifact_inputs,
        },
        selected_repo_refs=repo_refs_for_sources(sources),
        run_in_repo=request.run_in_repo,
        source_budget=source_budget,
        bundle=bundle,
    )
    project_payload = payload["project"]
    assert isinstance(project_payload, dict)
    final_prompt = bundle.composed_text
    return build_expanded_execution_request(
        request=request,
        final_prompt=final_prompt,
        composed_prompt=bundle.composed_text,
        sources=tuple(source.to_dict() for source in sources),
        repo_refs=repo_refs_for_sources(sources),
        run_in_repo=request.run_in_repo,
        save_target=request.save_target,
        save_mode=request.save_mode,
        source_summary=dict(project_payload.get("source_summary", {})),
        context_hash=bundle.content_hash,
        warnings=tuple(project_payload.get("warnings", ())),
    )


def record_execution_outcome(
    workspace_root: Path,
    *,
    request: ExecutionRequest,
    outcome: ExecutionOutcomeRecord,
) -> object:
    summary = execution_outcome_summary(outcome.best_text)
    if outcome.ok:
        return mark_stage_succeeded(
            workspace_root,
            request.item_ref,
            request.stage_id,
            summary=summary,
            save_target=request.save_target,
        )
    return mark_stage_failed(
        workspace_root,
        request.item_ref,
        request.stage_id,
        summary=summary,
    )


def _selection_from_request(request: ExecutionRequest):
    from taskledger.api.types import ExpandedSelection

    return ExpandedSelection(
        context_inputs=request.context_inputs,
        memory_inputs=request.memory_inputs,
        file_inputs=request.file_inputs,
        item_inputs=request.item_inputs,
        inline_inputs=request.inline_inputs,
        loop_artifact_inputs=request.loop_artifact_inputs,
    )
