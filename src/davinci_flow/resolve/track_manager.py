"""Gestor de pistas lógicas dedicadas en la línea de tiempo de DaVinci Resolve."""

from typing import Any

from davinci_flow.errors import DaVinciFlowError


class TrackManagementError(DaVinciFlowError):
    """Error al enumerar, crear o renombrar pistas en DaVinci Resolve."""


class ResolveTrackManager:
    """Administra y crea las pistas de vídeo y audio dedicadas (DF_CONTEXT, DF_MAIN, DF_ACCENT, DF_SFX)."""

    def __init__(self, timeline: Any) -> None:
        self.timeline = timeline

    def get_track_indices(self) -> dict[str, int]:
        """Localiza o planifica los índices de pistas dedicadas."""
        video_tracks_count = self._safe_get_track_count("video")
        audio_tracks_count = self._safe_get_track_count("audio")

        # Buscar pistas existentes por nombre
        video_mapping: dict[str, int] = {}
        for idx in range(1, video_tracks_count + 1):
            name = self._safe_get_track_name("video", idx)
            if name in ("DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_VISUAL_FX"):
                video_mapping[name] = idx

        audio_mapping: dict[str, int] = {}
        for idx in range(1, audio_tracks_count + 1):
            name = self._safe_get_track_name("audio", idx)
            if name == "DF_SFX":
                audio_mapping[name] = idx

        # Si no existen, asignar posiciones secuenciales
        curr_v = video_tracks_count
        if "DF_CONTEXT" not in video_mapping:
            curr_v += 1
            video_mapping["DF_CONTEXT"] = curr_v
        if "DF_MAIN" not in video_mapping:
            curr_v += 1
            video_mapping["DF_MAIN"] = curr_v
        if "DF_ACCENT" not in video_mapping:
            curr_v += 1
            video_mapping["DF_ACCENT"] = curr_v

        if "DF_SFX" not in audio_mapping:
            audio_mapping["DF_SFX"] = audio_tracks_count + 1

        return {**video_mapping, **audio_mapping}

    def ensure_dedicated_tracks(self) -> dict[str, int]:
        """Garantiza físicamente la creación y nombrado de las pistas en DaVinci Resolve."""
        track_map = self.get_track_indices()

        add_track_fn = getattr(self.timeline, "AddTrack", None)
        set_name_fn = getattr(self.timeline, "SetTrackName", None)

        if not callable(add_track_fn) or not callable(set_name_fn):
            return track_map

        # 1. Asegurar pistas de vídeo
        curr_v_count = self._safe_get_track_count("video")
        max_v_needed = max(
            track_map.get("DF_CONTEXT", 1),
            track_map.get("DF_MAIN", 1),
            track_map.get("DF_ACCENT", 1),
        )

        while curr_v_count < max_v_needed:
            try:
                add_track_fn("video")
                curr_v_count += 1
            except Exception:
                break

        # Asignar nombres a pistas de vídeo
        for name in ("DF_CONTEXT", "DF_MAIN", "DF_ACCENT"):
            idx = track_map.get(name)
            if idx:
                try:
                    set_name_fn("video", idx, name)
                except Exception:
                    pass

        # 2. Asegurar pista de audio para SFX
        curr_a_count = self._safe_get_track_count("audio")
        sfx_idx = track_map.get("DF_SFX", 1)
        while curr_a_count < sfx_idx:
            try:
                add_track_fn("audio")
                curr_a_count += 1
            except Exception:
                break

        try:
            set_name_fn("audio", sfx_idx, "DF_SFX")
        except Exception:
            pass

        return track_map

    def _safe_get_track_count(self, track_type: str) -> int:
        getter = getattr(self.timeline, "GetTrackCount", None)
        if not callable(getter):
            return 1
        try:
            return int(getter(track_type) or 1)
        except Exception:
            return 1

    def _safe_get_track_name(self, track_type: str, index: int) -> str:
        getter = getattr(self.timeline, "GetTrackName", None)
        if not callable(getter):
            return ""
        try:
            return str(getter(track_type, index) or "")
        except Exception:
            return ""
