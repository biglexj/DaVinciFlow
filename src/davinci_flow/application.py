"""Casos de uso iniciales de DaVinci Flow."""

from dataclasses import dataclass

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
