"""Escritor y gestor de marcadores en la línea de tiempo de DaVinci Resolve."""

from collections.abc import Sequence
from typing import Any

from davinci_flow.ai.aligner import TimelineMarker
from davinci_flow.errors import MarkerError


class ResolveMarkerWriter:
    """Inserta, consulta y limpia marcadores temáticos en la línea de tiempo activa de Resolve."""

    def __init__(self, timeline: Any) -> None:
        self._timeline = timeline

    def apply_markers(
        self,
        markers: Sequence[TimelineMarker],
        clear_existing_color: bool = False,
    ) -> int:
        """Inserta los marcadores en la línea de tiempo de Resolve de forma segura."""
        if not markers:
            return 0

        add_marker_fn = getattr(self._timeline, "AddMarker", None)
        if not callable(add_marker_fn):
            raise MarkerError(
                "La API de DaVinci Resolve no soporta AddMarker en este objeto de línea de tiempo."
            )

        if clear_existing_color:
            colors_to_clear = {m.color for m in markers}
            for c in colors_to_clear:
                self.clear_markers_by_color(c)

        applied_count = 0
        start_frame_offset = self._get_timeline_start_frame()

        for marker in markers:
            # Si el fotograma es relativo al inicio de la línea de tiempo
            target_frame = int(marker.frame)
            # Si el fotograma es 0-indexado relativo al proyecto y el timeline tiene offset (ej. 86400)
            if start_frame_offset > 0 and target_frame < start_frame_offset:
                target_frame += start_frame_offset

            try:
                # AddMarker(frameId, color, name, note, duration, customData)
                success = add_marker_fn(
                    target_frame,
                    marker.color,
                    marker.name,
                    marker.note,
                    max(1, int(marker.duration)),
                )
                if success is not False:
                    applied_count += 1
            except Exception:
                # Reintentar con firma simplificada (frameId, color, name, note, duration)
                try:
                    add_marker_fn(target_frame, marker.color, marker.name, marker.note)
                    applied_count += 1
                except Exception:
                    pass

        return applied_count

    def clear_markers_by_color(self, color: str) -> int:
        """Elimina los marcadores del color especificado en la línea de tiempo."""
        del_color_fn = getattr(self._timeline, "DeleteMarkersByColor", None)
        if callable(del_color_fn):
            try:
                res = del_color_fn(color)
                return 1 if res else 0
            except Exception:
                pass

        # Fallback: eliminar por fotograma consultando GetMarkers()
        get_markers_fn = getattr(self._timeline, "GetMarkers", None)
        del_frame_fn = getattr(self._timeline, "DeleteMarkerByFrame", None)
        if not callable(get_markers_fn) or not callable(del_frame_fn):
            return 0

        removed_count = 0
        try:
            current_markers = get_markers_fn() or {}
            for frame_id, data in list(current_markers.items()):
                if isinstance(data, dict) and data.get("color", "").casefold() == color.casefold():
                    try:
                        del_frame_fn(int(frame_id))
                        removed_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return removed_count

    def _get_timeline_start_frame(self) -> int:
        """Obtiene el fotograma inicial configurado en la línea de tiempo (ej. 86400 a 24fps para 01:00:00:00)."""
        get_start_fn = getattr(self._timeline, "GetStartFrame", None)
        if callable(get_start_fn):
            try:
                return int(get_start_fn() or 0)
            except Exception:
                return 0
        return 0
