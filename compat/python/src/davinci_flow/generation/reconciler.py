"""Motor de reconciliación y cálculo de diferencias para regeneración parcial."""

from dataclasses import dataclass
from typing import Sequence

from davinci_flow.generation.plan import GenerationPlan, build_generation_plan
from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.fingerprint import compute_cues_fingerprint
from davinci_flow.subtitles.model import SubtitleCue


@dataclass(frozen=True, slots=True)
class PlanDiff:
    """Diferencias detectadas entre una ejecución anterior y el estado actual de subtítulos."""

    previous_plan_id: str
    is_identical: bool
    added_blocks: tuple[CaptionBlock, ...]
    modified_blocks: tuple[CaptionBlock, ...]
    deleted_block_ids: tuple[str, ...]
    unchanged_blocks: tuple[CaptionBlock, ...]


def reconcile_subtitles(
    previous_plan: GenerationPlan,
    current_cues: Sequence[SubtitleCue],
) -> PlanDiff:
    """Compara el plan previo con los subtítulos actuales para regenerar selectivamente."""
    current_hash = compute_cues_fingerprint(current_cues)

    # Si la huella de origen coincide al 100%, el plan es idéntico (idempotencia perfecta)
    if previous_plan.source_hash == current_hash:
        return PlanDiff(
            previous_plan_id=previous_plan.plan_id,
            is_identical=True,
            added_blocks=(),
            modified_blocks=(),
            deleted_block_ids=(),
            unchanged_blocks=previous_plan.blocks,
        )

    # Construir un nuevo plan candidato con los subtítulos actuales
    new_plan = build_generation_plan(
        project_name=previous_plan.project_name,
        timeline_name=previous_plan.timeline_name,
        cues=current_cues,
        track_index=previous_plan.track_index,
        fps=previous_plan.fps,
        width=previous_plan.width,
        height=previous_plan.height,
        aspect_ratio=previous_plan.aspect_ratio,
        theme_name=previous_plan.theme_name,
        profile_name=previous_plan.profile_name,
        track_mapping=previous_plan.track_mapping,
    )

    prev_blocks_by_id = {b.id: b for b in previous_plan.blocks}
    new_blocks_by_id = {b.id: b for b in new_plan.blocks}

    unchanged: list[CaptionBlock] = []
    added: list[CaptionBlock] = []
    modified: list[CaptionBlock] = []
    deleted_ids: list[str] = []

    for block_id, new_block in new_blocks_by_id.items():
        if block_id in prev_blocks_by_id:
            prev_block = prev_blocks_by_id[block_id]
            if (
                prev_block.normalized_text == new_block.normalized_text
                and prev_block.start_frame == new_block.start_frame
                and prev_block.end_frame == new_block.end_frame
            ):
                unchanged.append(new_block)
            else:
                modified.append(new_block)
        else:
            added.append(new_block)

    for block_id in prev_blocks_by_id:
        if block_id not in new_blocks_by_id:
            deleted_ids.append(block_id)

    return PlanDiff(
        previous_plan_id=previous_plan.plan_id,
        is_identical=False,
        added_blocks=tuple(added),
        modified_blocks=tuple(modified),
        deleted_block_ids=tuple(deleted_ids),
        unchanged_blocks=tuple(unchanged),
    )
