"""Propuesta de rótulos instrumentales a partir de huecos de letra, sin escribir en Resolve."""

from dataclasses import dataclass
import math
import re

from davinci_flow.subtitles.model import SubtitleCue


@dataclass(frozen=True)
class InstrumentalLabel:
    start_frame: float
    end_frame: float
    text: str = 'INSTRUMENTAL'
    placement: str = 'bottom_left'
    animated: bool = False


def plan_instrumental_labels(cues: tuple[SubtitleCue, ...], start: float, end: float,
                            min_gap_frames: float = 0) -> tuple[InstrumentalLabel, ...]:
    """Devuelve huecos revisables. No determina acústicamente si hay instrumental."""
    if not all(math.isfinite(v) for v in (start, end, min_gap_frames)) or end <= start or min_gap_frames < 0:
        raise ValueError('Rango o duración mínima de hueco inválidos.')
    spans = []
    for cue in cues:
        normalized = re.sub(r'[\[\]()\s]+', '', cue.text).casefold()
        if not normalized or normalized == 'instrumental':
            continue
        a, b = max(start, cue.start_frame), min(end, cue.end_frame)
        if b > a:
            spans.append((a, b))
    cursor = start
    result = []
    for a, b in sorted(spans):
        if a > cursor and a - cursor >= min_gap_frames:
            result.append(InstrumentalLabel(cursor, a))
        cursor = max(cursor, b)
    if end > cursor and end - cursor >= min_gap_frames:
        result.append(InstrumentalLabel(cursor, end))
    return tuple(result)
