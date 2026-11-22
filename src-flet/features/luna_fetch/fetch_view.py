"""Vista Flet integrada de Luna Fetch para descarga e importación directa en DaVinci Resolve."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
import flet as ft

from davinci_flow.fetch.engine import FetchEngine
from davinci_flow.fetch.models import (
    FetchProgress,
    FetchRequest,
    FetchResult,
    MediaInfo,
    MediaKind,
)
from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, TEXT, button, card, field, select, text


class FetchView:
    """Pestaña de Luna Fetch para descargar recursos e importarlos al Media Pool de Resolve."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.analyzed_info: MediaInfo | None = None
        self.is_working: bool = False

        # Controles principales
        self.url_input = field(
            "Enlace del video o música",
            hint_text="https://www.youtube.com/watch?v=... o Suno, TikTok, SoundCloud",
            expand=True,
            on_submit=self._on_enter_pressed,
        )

        self.kind_selector = select(
            label="Tipo de medio",
            values={
                "video": "🎬 Video (MP4)",
                "audio": "🎵 Música / Audio (MP3)",
            },
            value="video",
            width=210,
            on_select=self._on_kind_changed,
        )

        self.import_checkbox = ft.Checkbox(
            label="Importar automáticamente en DaVinci Resolve",
            value=True,
            active_color=ACCENT,
            label_style=ft.TextStyle(size=12, color=TEXT),
        )

        self.btn_analyze = button(
            "Analizar",
            self.app.bind(self.analyze_link),
            icon=ft.Icons.SEARCH_ROUNDED,
        )

        self.btn_download = button(
            "Descargar e importar",
            self.app.bind(self.download_media),
            icon=ft.Icons.DOWNLOAD_ROUNDED,
            primary=True,
        )

        # Vista de previsualización de metadatos
        self.preview_image = ft.Image(
            src="",
            width=160,
            height=90,
            fit="cover",
            border_radius=8,
            visible=False,
        )
        self.preview_title = text("Pega un enlace para analizar metadatos", size=13, weight=ft.FontWeight.W_600)
        self.preview_sub = text("Compatible con YouTube, Suno AI, SoundCloud, TikTok y más de 1000 sitios.", size=11, color=MUTED)
        self.preview_badges = ft.Row([], spacing=6)

        self.preview_container = card(
            ft.Row([
                self.preview_image,
                ft.Column([
                    self.preview_title,
                    self.preview_sub,
                    self.preview_badges,
                ], spacing=6, expand=True),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=12,
        )

        # Barra de progreso y estado
        self.progress_bar = ft.ProgressBar(value=0.0, color=ACCENT, bgcolor=LINE, height=6, border_radius=3, visible=False)
        self.status_label = text("Listo para descargar.", size=12, color=MUTED)
        self.status_details = text("", size=11, color=MUTED)

        self.progress_container = card(
            ft.Column([
                ft.Row([
                    self.status_label,
                    ft.Container(expand=True),
                    self.status_details,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.progress_bar,
            ], spacing=8),
            padding=12,
        )

        # Lista de descargas recientes de la sesión
        self.history_column = ft.Column(spacing=6)
        self.history_container = card(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.HISTORY_ROUNDED, size=16, color=ACCENT),
                    text("Descargas de la sesión", size=13, weight=ft.FontWeight.W_600),
                ], spacing=8),
                self.history_column,
            ], spacing=10),
            padding=14,
        )

        # Contenedor raíz
        self.content = ft.Column([
            card(
                ft.Column([
                    ft.Row([
                        self.url_input,
                        self.btn_analyze,
                        self.btn_download,
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        self.kind_selector,
                        self.import_checkbox,
                        ft.Container(expand=True),
                        text("Destino en Resolve: Luna Fetch / (Videos o Música)", size=11, color=MUTED),
                    ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=12),
                padding=14,
            ),
            self.preview_container,
            self.progress_container,
            self.history_container,
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    async def _on_enter_pressed(self, e: Any = None) -> None:
        await self.analyze_link()

    async def _on_kind_changed(self, e: Any = None) -> None:
        self.app.page.update()

    async def analyze_link(self) -> None:
        url = (self.url_input.value or "").strip()
        if not url:
            self.status_label.value = "Ingresa un enlace antes de analizar."
            self.status_label.color = "#FF8B8B"
            self.app.page.update()
            return

        self.status_label.value = "Analizando enlace..."
        self.status_label.color = ACCENT
        self.status_details.value = ""
        self.progress_bar.visible = True
        self.progress_bar.value = None  # Indeterminado
        self.app.page.update()

        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(self.app.executor, FetchEngine.analyze, url)
            self.analyzed_info = info
            self.preview_title.value = info.title
            uploader_text = f"Subido por: {info.uploader}" if info.uploader else ""
            self.preview_sub.value = uploader_text

            if info.thumbnail_url:
                self.preview_image.src = info.thumbnail_url
                self.preview_image.visible = True
            else:
                self.preview_image.visible = False

            # Auto-seleccionar tipo de medio si es solo audio
            if info.is_audio:
                self.kind_selector.value = "audio"

            # Badges
            badges: list[ft.Control] = [
                ft.Container(
                    content=text(info.duration_display, size=10, color=TEXT),
                    bgcolor="#242C30",
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                    border_radius=4,
                ),
            ]
            if info.extractor:
                badges.append(
                    ft.Container(
                        content=text(info.extractor.capitalize(), size=10, color=ACCENT),
                        bgcolor="#173A35",
                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        border_radius=4,
                        border=ft.Border.all(0.6, ACCENT),
                    )
                )

            self.preview_badges.controls = badges
            self.status_label.value = "Análisis completado. Listo para descargar."
            self.status_label.color = TEXT
            self.progress_bar.visible = False

        except Exception as err:
            self.status_label.value = f"Error al analizar: {err}"
            self.status_label.color = "#FF8B8B"
            self.progress_bar.visible = False

        self.app.page.update()

    async def download_media(self) -> None:
        url = (self.url_input.value or "").strip()
        if not url:
            self.status_label.value = "Ingresa un enlace para descargar."
            self.status_label.color = "#FF8B8B"
            self.app.page.update()
            return

        if self.is_working:
            return

        self.is_working = True
        self.btn_download.disabled = True
        self.btn_analyze.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0.0
        self.status_label.value = "Iniciando descarga..."
        self.status_label.color = ACCENT
        self.status_details.value = ""
        self.app.page.update()

        media_kind = MediaKind.AUDIO if self.kind_selector.value == "audio" else MediaKind.VIDEO

        loop = asyncio.get_running_loop()

        def _on_progress(p: FetchProgress) -> None:
            # Planificar actualización en el bucle principal de interfaz
            asyncio.run_coroutine_threadsafe(self._update_progress_ui(p), loop)

        try:
            req = FetchRequest(url=url, kind=media_kind,
                               import_to_resolve=bool(self.import_checkbox.value))
            result: FetchResult = await loop.run_in_executor(
                self.app.executor,
                FetchEngine.download,
                req,
                _on_progress,
            )

            if result.success:
                dest_str = f"Guardado en {result.file_path.name}" if result.file_path else "Descarga finalizada"
                import_str = f" • Importado en {result.resolve_bin}" if result.imported_to_resolve else " • No importado en Resolve"
                self.status_label.value = f"✅ {dest_str}{import_str}"
                if result.error_message:
                    self.status_label.value += f'. {result.error_message}'
                self.status_label.color = ACCENT
                self.status_details.value = "100%"
                self.progress_bar.value = 1.0

                # Añadir al historial de sesión
                self._add_to_history(result)
            else:
                self.status_label.value = f"❌ Error: {result.error_message}"
                self.status_label.color = "#FF8B8B"
                self.status_details.value = ""
                self.progress_bar.visible = False

        except Exception as err:
            self.status_label.value = f"❌ Error inesperado: {err}"
            self.status_label.color = "#FF8B8B"
            self.progress_bar.visible = False

        finally:
            self.is_working = False
            self.btn_download.disabled = False
            self.btn_analyze.disabled = False
            self.app.page.update()

    async def _update_progress_ui(self, p: FetchProgress) -> None:
        if p.percent > 0:
            self.progress_bar.value = p.percent / 100.0
        details: list[str] = []
        if p.speed_text:
            details.append(p.speed_text)
        if p.eta_text:
            details.append(f"ETA: {p.eta_text}")
        self.status_details.value = " • ".join(details)
        if p.message:
            self.status_label.value = p.message
        self.app.page.update()

    def _add_to_history(self, result: FetchResult) -> None:
        is_video = result.kind == MediaKind.VIDEO
        icon = ft.Icons.MOVIE_ROUNDED if is_video else ft.Icons.MUSIC_NOTE_ROUNDED
        type_str = "Video" if is_video else "Música"

        resolve_status_badge = ft.Container(
            content=text("En Resolve" if result.imported_to_resolve else "Local", size=10, color=ACCENT if result.imported_to_resolve else MUTED),
            bgcolor="#173A35" if result.imported_to_resolve else "#202529",
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
            border_radius=4,
            border=ft.Border.all(0.6, ACCENT if result.imported_to_resolve else LINE),
        )

        item = ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=18, color=ACCENT),
                ft.Column([
                    ft.Row([
                        text(result.title or "Descarga", size=12.5, weight=ft.FontWeight.W_600),
                        resolve_status_badge,
                    ], spacing=8),
                    text(str(result.file_path) if result.file_path else result.url, size=11, color=MUTED, selectable=True),
                ], spacing=2, expand=True),
                button(
                    "Abrir carpeta",
                    lambda _: self._open_folder(result.file_path.parent if result.file_path else None),
                    icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            bgcolor="#161A1D",
            border_radius=8,
            border=ft.Border.all(1, LINE),
        )
        self.history_column.controls.insert(0, item)
        self.app.page.update()

    def _open_folder(self, folder: Path | None) -> None:
        if folder and folder.is_dir():
            import subprocess
            subprocess.Popen(["explorer.exe", str(folder)])
