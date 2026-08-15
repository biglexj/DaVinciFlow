"""Lectura no destructiva de subtítulos desde una línea de tiempo de Resolve."""

from typing import Any

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.subtitles import SubtitleCue


class ResolveSubtitleReader:
    """Traduce objetos de subtítulo de Resolve al modelo interno."""

    def __init__(self, timeline: Any) -> None:
        self._timeline = timeline

    def read_track(self, track_index: int = 1) -> tuple[SubtitleCue, ...]:
        """Lee y ordena los bloques de una pista de subtítulos."""

        track_count = int(self._timeline.GetTrackCount("subtitle") or 0)
        if track_count == 0:
            raise SubtitleTrackError("La línea de tiempo no contiene pistas de subtítulos.")
        if track_index < 1 or track_index > track_count:
            raise SubtitleTrackError(
                f"La pista {track_index} no existe. Hay {track_count} pista(s) de subtítulos."
            )

        items = self._timeline.GetItemListInTrack("subtitle", track_index) or []
        cues: list[SubtitleCue] = []
        for item in items:
            text = str(item.GetName() or "").strip()
            if not text:
                continue
            cues.append(
                SubtitleCue(
                    text=text,
                    start_frame=float(item.GetStart(False)),
                    end_frame=float(item.GetEnd(False)),
                    track_index=track_index,
                )
            )

        cues.sort(key=lambda cue: (cue.start_frame, cue.end_frame))
        return tuple(cues)
