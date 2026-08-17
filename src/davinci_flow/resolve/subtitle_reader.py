"""Lectura no destructiva y robusta de subtítulos desde una línea de tiempo de Resolve."""

from typing import Any

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.subtitles import SubtitleCue


def _extract_subtitle_text(item: Any) -> str:
    """Extrae el contenido textual de un elemento de subtítulo con múltiples estrategias de respaldo."""
    # 1. Nombre principal del clip / subtítulo
    name_fn = getattr(item, "GetName", None)
    if callable(name_fn):
        try:
            name = str(name_fn() or "").strip()
            if name:
                return name
        except Exception:
            pass

    # 2. Propiedad interna 'Text' o 'Clip Name'
    prop_fn = getattr(item, "GetProperty", None)
    if callable(prop_fn):
        for prop_key in ("Text", "Clip Name", "SubtitleText"):
            try:
                val = str(prop_fn(prop_key) or "").strip()
                if val:
                    return val
            except Exception:
                continue

    # 3. Composición Fusion embebida
    fusion_comp_fn = getattr(item, "GetFusionCompByIndex", None)
    if callable(fusion_comp_fn):
        try:
            comp = fusion_comp_fn(1)
            if comp:
                tools = comp.GetToolList(False, "TextPlus") or comp.GetToolList()
                tool_list = tools.values() if isinstance(tools, dict) else (tools or [])
                for tool in tool_list:
                    if hasattr(tool, "StyledText"):
                        text_val = str(tool.StyledText[1] or "").strip()
                        if text_val:
                            return text_val
        except Exception:
            pass

    return ""


def _extract_frame(item: Any, method_name: str, fallback_prop: str) -> float:
    """Obtiene el número de fotograma de inicio o fin de forma compatible entre versiones de Resolve."""
    fn = getattr(item, method_name, None)
    if callable(fn):
        # Intentar primero con argumento False (tiempo relativo)
        try:
            val = fn(False)
            if val is not None:
                return float(val)
        except Exception:
            pass
        # Intentar sin argumentos
        try:
            val = fn()
            if val is not None:
                return float(val)
        except Exception:
            pass

    prop_fn = getattr(item, "GetProperty", None)
    if callable(prop_fn):
        try:
            val = prop_fn(fallback_prop)
            if val is not None:
                return float(val)
        except Exception:
            pass

    return 0.0


class ResolveSubtitleReader:
    """Traduce objetos de subtítulo de Resolve al modelo interno."""

    def __init__(self, timeline: Any) -> None:
        self._timeline = timeline

    def read_track(self, track_index: int = 1) -> tuple[SubtitleCue, ...]:
        """Lee y ordena los bloques de una pista de subtítulos."""
        get_track_count = getattr(self._timeline, "GetTrackCount", None)
        track_count = int(get_track_count("subtitle") or 0) if callable(get_track_count) else 0

        if track_count == 0:
            raise SubtitleTrackError("La línea de tiempo no contiene pistas de subtítulos.")
        if track_index < 1 or track_index > track_count:
            raise SubtitleTrackError(
                f"La pista {track_index} no existe. Hay {track_count} pista(s) de subtítulos."
            )

        items = self._timeline.GetItemListInTrack("subtitle", track_index) or []
        cues: list[SubtitleCue] = []
        for item in items:
            text = _extract_subtitle_text(item)
            if not text:
                continue

            start_f = _extract_frame(item, "GetStart", "Start")
            end_f = _extract_frame(item, "GetEnd", "End")

            cues.append(
                SubtitleCue(
                    text=text,
                    start_frame=start_f,
                    end_frame=end_f,
                    track_index=track_index,
                )
            )

        cues.sort(key=lambda cue: (cue.start_frame, cue.end_frame))
        return tuple(cues)
