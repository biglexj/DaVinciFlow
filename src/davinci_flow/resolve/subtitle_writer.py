"""Escritor de subtítulos en la pista nativa de subtítulos de DaVinci Resolve.

La API de scripting de Resolve 21.1 **no permite crear cues de subtítulo de forma
directa**: solo expone ``CreateSubtitlesFromAudio`` para el subtitulado automático. El
camino soportado es, por tanto:

1. Escribir un archivo ``.srt`` con los tiempos calculados sobre los fotogramas de la
   línea de tiempo.
2. Importar ese ``.srt`` al Media Pool (Resolve lo reconoce como elemento de subtítulo).
3. Anexarlo a una pista de tipo ``subtitle`` y **verificar** que los cues llegaron.

Como el parámetro ``mediaType`` del API solo documenta vídeo (1) y audio (2), el
anexado se intenta con varias variantes y se comprueba el resultado en cada intento.
Si ninguna funciona, se conserva el ``.srt`` en disco y se informa de la ruta exacta
para importarlo a mano: el archivo nunca se pierde.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.subtitles.model import SubtitleCue

DEFAULT_FRAME_RATE = 24.0
SRT_EXTENSION = ".srt"


@dataclass(frozen=True, slots=True)
class SubtitleWriteResult:
    """Confirmación de la escritura de subtítulos."""

    track_index: int
    cue_count: int
    srt_path: str
    confirmed: bool
    method: str = ""
    detail: str = ""


def format_srt_timestamp(seconds: float) -> str:
    """Convierte segundos a la marca de tiempo SRT (``HH:MM:SS,mmm``)."""
    if seconds < 0:
        raise SubtitleTrackError("El tiempo de un subtítulo no puede ser negativo.")
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(cues: Sequence[SubtitleCue], frame_rate: float = DEFAULT_FRAME_RATE) -> str:
    """Construye el contenido de un archivo SRT a partir de cues en fotogramas."""
    if frame_rate <= 0:
        raise SubtitleTrackError("La tasa de fotogramas debe ser positiva.")
    if not cues:
        raise SubtitleTrackError("No hay subtítulos que escribir.")

    blocks: list[str] = []
    for index, cue in enumerate(cues, start=1):
        start = format_srt_timestamp(cue.start_frame / frame_rate)
        end = format_srt_timestamp(cue.end_frame / frame_rate)
        blocks.append(f"{index}\n{start} --> {end}\n{cue.text.strip()}\n")
    return "\n".join(blocks)


def write_srt(cues: Sequence[SubtitleCue], path: Path, frame_rate: float = DEFAULT_FRAME_RATE) -> Path:
    """Escribe los cues en un archivo SRT y devuelve la ruta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_srt(cues, frame_rate), encoding="utf-8")
    return path


class SubtitleTrackWriter:
    """Escribe subtítulos en la pista nativa de la línea de tiempo activa."""

    def __init__(self, session: Any, temp_root: Path | None = None) -> None:
        self.session = session
        self.timeline = session.timeline
        self.media_pool = session.project.GetMediaPool()
        if self.media_pool is None:
            raise SubtitleTrackError("El proyecto activo no expone el Media Pool.")
        self.temp_root = temp_root or Path.home() / ".davinci_flow" / "subtitles"

    def frame_rate(self) -> float:
        """Devuelve la tasa de fotogramas de la línea de tiempo."""
        for getter in (getattr(self.timeline, "GetSettings", None), getattr(self.session.project, "GetSettings", None)):
            if not callable(getter):
                continue
            try:
                settings = getter() or {}
            except Exception:
                continue
            value = settings.get("timelineFrameRate") if isinstance(settings, dict) else None
            try:
                rate = float(value)
            except (TypeError, ValueError):
                continue
            if rate > 0:
                return rate
        return DEFAULT_FRAME_RATE

    def ensure_track(self) -> int:
        """Devuelve el índice de la primera pista de subtítulos; la crea si no existe."""
        count = int(self.timeline.GetTrackCount("subtitle") or 0)
        if count > 0:
            return 1
        add_track = getattr(self.timeline, "AddTrack", None)
        if not callable(add_track):
            raise SubtitleTrackError("Esta versión de Resolve no permite crear pistas de subtítulos.")
        if not add_track("subtitle"):
            raise SubtitleTrackError("Resolve no confirmó la creación de la pista de subtítulos.")
        return 1

    def write(
        self,
        cues: Sequence[SubtitleCue],
        track_index: int | None = None,
        file_name: str = "davinci-flow",
    ) -> SubtitleWriteResult:
        """Escribe los cues en la pista de subtítulos y verifica el resultado."""
        if not cues:
            raise SubtitleTrackError("No hay subtítulos que escribir.")

        rate = self.frame_rate()
        target_track = track_index or self.ensure_track()

        self.temp_root.mkdir(parents=True, exist_ok=True)
        srt_path = self.temp_root / f"{file_name}{SRT_EXTENSION}"
        write_srt(cues, srt_path, rate)

        item = self._import_media(str(srt_path))
        before = self._count_items(target_track)

        attempts = (
            ("mediaType=2", 2),
            ("mediaType=1", 1),
            ("sin mediaType", None),
        )
        for method, media_type in attempts:
            appended = self._append(item, target_track, media_type)
            after = self._count_items(target_track)
            if appended and after > before:
                return SubtitleWriteResult(
                    track_index=target_track,
                    cue_count=len(cues),
                    srt_path=str(srt_path),
                    confirmed=True,
                    method=method,
                )
            if appended:
                # Resolve aceptó el elemento pero la pista no creció: se deshace para no dejar rastro.
                self._delete_items(appended)

        raise SubtitleTrackError(
            "Resolve no aceptó los subtítulos en la pista nativa. "
            f"El archivo SRT quedó en {srt_path}; impórtalo desde el Media Pool para colocarlo a mano."
        )

    def _count_items(self, track_index: int) -> int:
        """Cuenta los elementos de la pista de subtítulos."""
        items = self.timeline.GetItemListInTrack("subtitle", track_index) or []
        if isinstance(items, dict):
            items = list(items.values())
        return len(items)

    def _import_media(self, path: str) -> Any:
        """Importa el SRT al Media Pool."""
        import_fn = getattr(self.media_pool, "ImportMedia", None)
        if not callable(import_fn):
            raise SubtitleTrackError("El Media Pool no expone ImportMedia.")
        imported = import_fn([{"FilePath": path}])
        if not imported:
            raise SubtitleTrackError(f"Resolve no pudo importar el archivo: {path}")
        if isinstance(imported, dict):
            imported = list(imported.values())
        return imported[0]

    def _append(self, item: Any, track_index: int, media_type: int | None) -> list[Any]:
        """Anexa el elemento de subtítulo a la pista indicada."""
        append_fn = getattr(self.media_pool, "AppendToTimeline", None)
        if not callable(append_fn):
            raise SubtitleTrackError("El Media Pool no expone AppendToTimeline.")

        clip_info: dict[str, Any] = {
            "mediaPoolItem": item,
            "trackIndex": track_index,
        }
        if media_type is not None:
            clip_info["mediaType"] = media_type

        result = append_fn([clip_info])
        if isinstance(result, dict):
            result = list(result.values())
        return list(result or [])

    def _delete_items(self, items: Sequence[Any]) -> None:
        """Elimina elementos; los fallos no ocultan el error original."""
        if not items:
            return
        try:
            self.timeline.DeleteClips(list(items), False)
        except Exception:
            pass
