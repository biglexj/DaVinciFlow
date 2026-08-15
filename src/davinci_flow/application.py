"""Casos de uso principales y orquestación de DaVinci Flow."""

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from davinci_flow.generation.plan import GenerationPlan, build_generation_plan
from davinci_flow.generation.reconciler import PlanDiff, reconcile_subtitles
from davinci_flow.generation.record import GenerationExecutionRecord
from davinci_flow.resolve import (
    ResolveSubtitleReader,
    ResolveTimelineWriter,
    connect_to_resolve,
)
from davinci_flow.sfx.engine import SFXProposalEngine
from davinci_flow.subtitles import SubtitleCue


@dataclass(frozen=True, slots=True)
class SubtitleScan:
    """Resultado de leer subtítulos de la línea de tiempo activa."""

    project_name: str
    timeline_name: str
    track_index: int
    cues: tuple[SubtitleCue, ...]


def scan_active_subtitles(track_index: int = 1) -> SubtitleScan:
    """Conecta con Resolve y obtiene una instantánea de la pista solicitada."""
    session = connect_to_resolve()
    cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    return SubtitleScan(
        project_name=str(session.project.GetName()),
        timeline_name=str(session.timeline.GetName()),
        track_index=track_index,
        cues=cues,
    )


def plan_active_subtitles(
    track_index: int = 1,
    theme_name: str = "ely",
    profile_name: str = "natural",
    enable_sfx: bool = True,
) -> GenerationPlan:
    """Lee la pista activa y produce un GenerationPlan clasificado con propuestas de SFX."""
    session = connect_to_resolve()
    cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    base_plan = build_generation_plan(
        project_name=str(session.project.GetName()),
        timeline_name=str(session.timeline.GetName()),
        cues=cues,
        track_index=track_index,
        theme_name=theme_name,
        profile_name=profile_name,
    )

    if enable_sfx:
        sfx_engine = SFXProposalEngine()
        processed_blocks = sfx_engine.process_blocks(base_plan.blocks, profile_name=profile_name)
        return GenerationPlan(
            plan_id=base_plan.plan_id,
            project_name=base_plan.project_name,
            timeline_name=base_plan.timeline_name,
            timeline_id=base_plan.timeline_id,
            track_index=base_plan.track_index,
            start_frame=base_plan.start_frame,
            end_frame=base_plan.end_frame,
            fps=base_plan.fps,
            width=base_plan.width,
            height=base_plan.height,
            aspect_ratio=base_plan.aspect_ratio,
            theme_name=base_plan.theme_name,
            profile_name=base_plan.profile_name,
            source_hash=base_plan.source_hash,
            track_mapping=base_plan.track_mapping,
            blocks=processed_blocks,
        )

    return base_plan


def generate_from_active_timeline(
    track_index: int = 1,
    theme_name: str = "ely",
    profile_name: str = "natural",
    enable_sfx: bool = True,
    dry_run: bool = False,
) -> GenerationExecutionRecord:
    """Ejecuta el flujo completo de análisis, planificación y generación en Resolve."""
    session = connect_to_resolve()
    plan = plan_active_subtitles(
        track_index=track_index,
        theme_name=theme_name,
        profile_name=profile_name,
        enable_sfx=enable_sfx,
    )
    writer = ResolveTimelineWriter(session.timeline)
    return writer.apply_plan(plan, dry_run=dry_run)


def reconcile_active_timeline(
    previous_plan_path: str | Path,
    track_index: int = 1,
) -> PlanDiff:
    """Calcula diferencias entre un plan previo y el estado actual de subtítulos."""
    session = connect_to_resolve()
    previous_plan = GenerationPlan.load_from_file(previous_plan_path)
    current_cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    return reconcile_subtitles(previous_plan, current_cues)
