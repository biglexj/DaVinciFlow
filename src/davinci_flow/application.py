"""Casos de uso de DaVinci Flow."""

from dataclasses import dataclass

from davinci_flow.generation.plan import GenerationPlan, build_generation_plan
from davinci_flow.resolve import ResolveSubtitleReader, connect_to_resolve
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
) -> GenerationPlan:
    """Lee la pista activa y produce un GenerationPlan clasificado sin modificar Resolve."""
    session = connect_to_resolve()
    cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    return build_generation_plan(
        project_name=str(session.project.GetName()),
        timeline_name=str(session.timeline.GetName()),
        cues=cues,
        track_index=track_index,
        theme_name=theme_name,
        profile_name=profile_name,
    )
