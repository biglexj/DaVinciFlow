"""Modelos y contratos para la integración de descarga de medios (Luna Fetch)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


class MediaKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Metadatos extraídos de una URL antes o durante la descarga."""

    url: str
    title: str
    duration_seconds: float = 0.0
    thumbnail_url: str | None = None
    uploader: str | None = None
    extractor: str | None = None
    is_audio: bool = False

    @property
    def duration_display(self) -> str:
        if self.duration_seconds <= 0:
            return "--:--"
        mins = int(self.duration_seconds // 60)
        secs = int(self.duration_seconds % 60)
        return f"{mins}:{secs:02d}"


@dataclass(frozen=True, slots=True)
class FetchProgress:
    """Estado y porcentaje de avance durante la descarga o procesamiento."""

    phase: str  # "starting" | "downloading" | "processing" | "importing" | "completed" | "error"
    percent: float = 0.0
    speed_text: str = ""
    eta_text: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    message: str = ""


@dataclass
class FetchRequest:
    """Solicitud de descarga de medio con opciones de formato e importación."""

    url: str
    kind: MediaKind = MediaKind.VIDEO
    audio_format: str = "mp3"  # "mp3", "m4a", "wav"
    video_format: str = "mp4"
    output_dir: Path | None = None
    import_to_resolve: bool = True
    custom_bin_name: str | None = None

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname:
            raise ValueError('Ingresa un enlace HTTP o HTTPS válido.')
        if not isinstance(self.kind, MediaKind):
            raise ValueError('El tipo debe ser video o audio.')
        if type(self.import_to_resolve) is not bool:
            raise ValueError('La opción de importación debe ser booleana.')
        if self.audio_format not in {'mp3', 'm4a', 'wav', 'flac'} or self.video_format != 'mp4':
            raise ValueError('Formato de descarga no admitido.')


@dataclass
class FetchResult:
    """Resultado final de la descarga e importación."""

    success: bool
    url: str
    title: str = ""
    file_path: Path | None = None
    kind: MediaKind = MediaKind.VIDEO
    imported_to_resolve: bool = False
    resolve_bin: str | None = None
    error_message: str | None = None
    raw_info: dict[str, Any] = field(default_factory=dict)
