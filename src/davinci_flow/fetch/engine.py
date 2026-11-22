"""Motor autónomo de descarga e inspección de medios para DaVinci Flow (Luna Fetch)."""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Callable

import yt_dlp

from davinci_flow.fetch.models import (
    FetchProgress,
    FetchRequest,
    FetchResult,
    MediaInfo,
    MediaKind,
)
from davinci_flow.fetch.resolve_importer import ResolveMediaImporter

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows/macOS/Linux."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


class FetchEngine:
    """Motor de análisis y descarga multiformato basado en yt-dlp y FFmpeg."""

    @staticmethod
    def get_default_base_dir() -> Path:
        """Devuelve la carpeta base por defecto para las descargas de Luna Fetch."""
        downloads_dir = Path.home() / "Downloads"
        if not downloads_dir.exists():
            downloads_dir = Path.home()
        return downloads_dir / "LunaFetch"

    @classmethod
    def resolve_destination(cls, base_dir: Path | None, kind: MediaKind) -> Path:
        """Resuelve la subcarpeta de destino según el estándar de Luna Fetch.

        Las descargas de video van a 'Videos' y las sonoras a 'Música'.
        """
        base = base_dir or cls.get_default_base_dir()
        subfolder = "Videos" if kind == MediaKind.VIDEO else "Música"

        # Si la ruta ya termina en la subcarpeta correspondiente, no anidarla dos veces
        aliases = ('videos', 'video') if kind == MediaKind.VIDEO else ('música', 'musica', 'audio')
        if base.name.casefold() in aliases:
            final_dir = base
        else:
            final_dir = base / subfolder

        final_dir.mkdir(parents=True, exist_ok=True)
        return final_dir

    @classmethod
    def analyze(cls, url: str) -> MediaInfo:
        """Analiza un enlace y devuelve los metadatos esenciales sin descargar."""
        ydl_opts: dict[str, Any] = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as err:
                raise RuntimeError(f"No se pudo analizar el enlace: {err}") from err

            if info is None:
                raise RuntimeError("yt-dlp no devolvió información para el enlace indicado.")
            if info.get('_type') in {'playlist', 'multi_video'}:
                raise RuntimeError('Usa el enlace de un único vídeo o audio.')

            title = info.get("title") or "Sin título"
            duration = float(info.get("duration") or 0.0)
            thumbnail = info.get("thumbnail")
            uploader = info.get("uploader") or info.get("channel")
            extractor = info.get("extractor")

            # Detectar si el recurso es intrínsecamente solo audio (SoundCloud, Suno, etc.)
            formats = info.get("formats") or []
            is_audio_only = bool(
                extractor in ("soundcloud", "suno")
                or (formats and all(f.get("vcodec") == "none" for f in formats if f.get("url")))
            )

            return MediaInfo(
                url=url,
                title=title,
                duration_seconds=duration,
                thumbnail_url=thumbnail,
                uploader=uploader,
                extractor=extractor,
                is_audio=is_audio_only,
            )

    @classmethod
    def download(
        cls,
        request: FetchRequest,
        progress_callback: Callable[[FetchProgress], None] | None = None,
    ) -> FetchResult:
        """Descarga el medio solicitado y opcionalmente lo importa en DaVinci Resolve."""
        target_dir = cls.resolve_destination(request.output_dir, request.kind)
        downloaded_paths: list[Path] = []
        ffmpeg = shutil.which('ffmpeg')
        if request.kind == MediaKind.AUDIO and not ffmpeg:
            return FetchResult(False, request.url, kind=request.kind,
                               error_message='FFmpeg no está disponible para convertir el audio.')

        def _progress_hook(d: dict[str, Any]) -> None:
            if progress_callback is None:
                return

            status = d.get("status", "")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                percent = 0.0
                if total > 0:
                    percent = min(100.0, max(0.0, (downloaded / total) * 100.0))

                speed_str = d.get("_speed_str") or ""
                eta_str = d.get("_eta_str") or ""

                progress_callback(
                    FetchProgress(
                        phase="downloading",
                        percent=percent,
                        speed_text=speed_str,
                        eta_text=eta_str,
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        message=f"Descargando: {percent:.1f}% ({speed_str})",
                    )
                )
            elif status == "finished":
                filename = d.get("filename")
                if filename:
                    downloaded_paths.append(Path(filename))
                progress_callback(
                    FetchProgress(
                        phase="processing",
                        percent=100.0,
                        message="Finalizando y procesando archivo...",
                    )
                )

        output_template = str(target_dir / "%(title).180B [%(id)s].%(ext)s")

        ydl_opts: dict[str, Any] = {
            "outtmpl": output_template,
            "progress_hooks": [_progress_hook],
            "post_hooks": [lambda filename: downloaded_paths.insert(0, Path(filename))],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if ffmpeg:
            ydl_opts['ffmpeg_location'] = ffmpeg

        if request.kind == MediaKind.AUDIO:
            codec = request.audio_format if request.audio_format in ("mp3", "m4a", "wav", "flac") else "mp3"
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": codec,
                        "preferredquality": "192",
                    }
                ],
            })
        else:
            # Video: MP4 con audio AAC si es posible
            ydl_opts.update({
                "format": ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" if ffmpeg
                           else "best[ext=mp4][vcodec!=none][acodec!=none]"),
                "merge_output_format": "mp4",
            })

        if progress_callback:
            progress_callback(
                FetchProgress(phase="starting", percent=0.0, message="Conectando con el servidor...")
            )

        extracted_title = ""
        raw_info: dict[str, Any] = {}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                if info and info.get('_type') in {'playlist', 'multi_video'}:
                    raise RuntimeError('Usa el enlace de un único vídeo o audio.')
                if info:
                    info = ydl.process_ie_result(info, download=True)
                if info:
                    raw_info = info
                    extracted_title = info.get("title") or ""
                    # En algunos casos requested_downloads contiene el path final posprocesado
                    if info.get('filepath'):
                        downloaded_paths.insert(0, Path(info['filepath']))
                    req_dl = info.get("requested_downloads")
                    if isinstance(req_dl, list) and len(req_dl) == 1 and req_dl[0].get("filepath"):
                        downloaded_paths.append(Path(req_dl[0]["filepath"]))

        except Exception as err:
            err_msg = str(err)
            if progress_callback:
                progress_callback(FetchProgress(phase="error", percent=0.0, message=err_msg))
            return FetchResult(
                success=False,
                url=request.url,
                title=extracted_title,
                kind=request.kind,
                error_message=err_msg,
            )

        # Determinar el archivo final en el disco
        final_file: Path | None = None
        for p in downloaded_paths:
            if p.exists() and p.is_file():
                final_file = p
                break

        if final_file is None or not final_file.exists():
            return FetchResult(
                success=False,
                url=request.url,
                title=extracted_title,
                kind=request.kind,
                error_message="La descarga finalizó pero no se localizó el archivo resultante en disco.",
            )

        imported_ok = False
        resolve_bin_label: str | None = None
        import_error: str | None = None

        if request.import_to_resolve:
            if progress_callback:
                progress_callback(
                    FetchProgress(phase="importing", percent=100.0, message="Importando al Media Pool de Resolve...")
                )
            imported_ok, resolve_bin_label = ResolveMediaImporter.import_to_resolve(
                file_path=final_file,
                kind=request.kind,
                custom_bin_name=request.custom_bin_name,
            )
            if not imported_ok:
                import_error, resolve_bin_label = resolve_bin_label, None

        if progress_callback:
            done_msg = "Descarga e importación completadas." if imported_ok else "Descarga completada en disco."
            progress_callback(
                FetchProgress(phase="completed", percent=100.0, message=done_msg)
            )

        return FetchResult(
            success=True,
            url=request.url,
            title=extracted_title or final_file.stem,
            file_path=final_file,
            kind=request.kind,
            imported_to_resolve=imported_ok,
            resolve_bin=resolve_bin_label,
            error_message=import_error,
            raw_info=raw_info,
        )
