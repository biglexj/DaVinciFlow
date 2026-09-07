"""Lectura no destructiva y robusta de subtítulos desde una línea de tiempo de Resolve."""

from typing import Any

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.subtitles import SubtitleCue


def _extract_subtitle_text(item: Any, fallback_index: int = 1) -> str:
    """Extrae el contenido textual de un elemento de subtítulo o clip Text+ con múltiples estrategias de respaldo."""
    # 1. Intentar leer desde la composición Fusion si es un clip Text+/Título
    get_fusion_comp = getattr(item, "GetFusionCompByIndex", None)
    if callable(get_fusion_comp):
        try:
            comp = get_fusion_comp(1)
            if comp is not None:
                get_tools = getattr(comp, "GetToolList", None)
                if callable(get_tools):
                    tools = get_tools() or {}
                    for tool in tools.values():
                        get_attrs = getattr(tool, "GetAttrs", None)
                        reg_id = get_attrs("TOOLS_RegID") if callable(get_attrs) else ""
                        if reg_id in ("TextPlus", "Fuse.TextPlus"):
                            get_inp = getattr(tool, "GetInput", None)
                            styled_val = get_inp("StyledText") if callable(get_inp) else getattr(tool, "StyledText", None)
                            if styled_val and str(styled_val).strip():
                                return str(styled_val).strip()
        except Exception:
            pass

    # 2. Intentar leer el nombre nativo
    name_fn = getattr(item, "GetName", None)
    if callable(name_fn):
        try:
            name = str(name_fn() or "").strip()
            if name:
                return name
        except Exception:
            pass

    # 3. Intentar propiedades estándar
    prop_fn = getattr(item, "GetProperty", None)
    if callable(prop_fn):
        for prop_key in ("Text", "Clip Name", "SubtitleText", "Subtitle", "Name"):
            try:
                val = str(prop_fn(prop_key) or "").strip()
                if val:
                    return val
            except Exception:
                continue

    return ""


def _extract_frame(item: Any, method_name: str, fallback_prop: str) -> float:
    """Obtiene el número de fotograma de inicio o fin de forma compatible entre versiones de Resolve."""
    fn = getattr(item, method_name, None)
    if callable(fn):
        try:
            val = fn(False)
            if val is not None:
                return float(val)
        except Exception:
            pass
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
    """Traduce objetos de subtítulo y pistas de vídeo con Text+ de Resolve al modelo interno."""

    def __init__(self, timeline: Any) -> None:
        self._timeline = timeline

    def read_track(
        self,
        track_index: int = 1,
        track_type: str = "subtitle",
    ) -> tuple[SubtitleCue, ...]:
        """Lee y ordena los bloques de una pista de subtítulos o pista de vídeo con títulos Text+."""
        get_track_count = getattr(self._timeline, "GetTrackCount", None)
        track_count = int(get_track_count(track_type) or 0) if callable(get_track_count) else 0

        if track_count == 0:
            if track_type == "subtitle":
                raise SubtitleTrackError("La línea de tiempo no contiene pistas de subtítulos.")
            raise SubtitleTrackError(f"La línea de tiempo no contiene pistas de {track_type}.")

        if track_index < 1 or track_index > track_count:
            raise SubtitleTrackError(
                f"La pista {track_type} {track_index} no existe. Hay {track_count} pista(s) de {track_type}."
            )

        items = self._timeline.GetItemListInTrack(track_type, track_index) or []
        cues: list[SubtitleCue] = []
        for idx, item in enumerate(items, start=1):
            text = _extract_subtitle_text(item, fallback_index=idx)
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

    def read_auto(self) -> tuple[SubtitleCue, ...]:
        """Intenta leer primero de la pista de subtítulos 1; si está vacía, busca en pistas de vídeo con Text+."""
        try:
            cues = self.read_track(track_index=1, track_type="subtitle")
            if cues:
                return cues
        except Exception:
            pass

        get_track_count = getattr(self._timeline, "GetTrackCount", None)
        video_track_count = int(get_track_count("video") or 0) if callable(get_track_count) else 0
        for v_idx in range(1, video_track_count + 1):
            try:
                cues = self.read_track(track_index=v_idx, track_type="video")
                if cues:
                    return cues
            except Exception:
                continue

        return ()

