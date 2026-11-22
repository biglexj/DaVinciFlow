"""Vista especializada de Efectos de Sonido (SFX) para DaVinci Flow con preescucha interactiva."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
import flet as ft

from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS
from davinci_flow.sfx.player import global_sound_player
from shared.components import ACCENT, LINE, MUTED, TEXT, button, card, field, select, text

PAGE_SIZE = 48


@dataclass
class SoundEntry:
    id: str
    name: str
    category: str
    subpath: str
    full_path: str
    ext: str
    is_procedural: bool = False


class SFXView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.query_field = field("Buscar sonido por nombre o palabra clave…", expand=True, on_change=self.app.bind(self.on_filter_changed))
        self.category_dropdown = select(
            "Tipo / Subcarpeta",
            {"all": "Todos los efectos"},
            "all",
            240,
            on_select=self.app.bind(self.on_filter_changed),
        )
        self.track_name = field("Pista SFX", "DF_SFX", width=120)
        self.anticipation = field("Anticipación (frames)", "-3", width=160, hint_text="Disparo previo al subtítulo")
        
        self.offset = 0
        self.list_column = ft.GridView(expand=True, max_extent=128, child_aspect_ratio=1.0,
                                       spacing=10, run_spacing=10, padding=4)
        self.previous_button = button('Anterior', app.bind(self.paginate, -1))
        self.next_button = button('Siguiente', app.bind(self.paginate, 1))
        self.status_banner = text("Cargando catálogo sonoro…", color=MUTED, size=12)
        self.now_playing_text = text("Ningún sonido en reproducción", color=MUTED, size=11)
        self.currently_playing: str | None = None
        
        self.all_sounds: list[SoundEntry] = []
        self.categories: dict[str, int] = {}
        self._indexed_paths = None
        self._load_lock = asyncio.Lock()

        config_card = card(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TUNE_ROUNDED, color=ACCENT, size=18),
                    text("Ajustes de inyección sonora en Resolve:", size=13, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Row([
                    self.track_name,
                    self.anticipation,
                    button(
                        "Ir a Biblioteca SFX",
                        self.app.bind(self.go_to_library_sfx),
                        ft.Icons.FOLDER_OPEN_OUTLINED,
                        tooltip="Configurar carpetas adicionales de efectos de sonido",
                    ),
                    button(
                        "Reindexar carpeta",
                        self.app.bind(self.reindex),
                        ft.Icons.REFRESH_ROUNDED,
                        tooltip="Volver a escanear archivos de audio en disco",
                    ),
                ], wrap=True, spacing=10, run_spacing=8),
            ], spacing=10),
            padding=12,
        )

        status_card = card(
            ft.Row([
                ft.Icon(ft.Icons.GRAPHIC_EQ_ROUNDED, color=ACCENT, size=18),
                self.status_banner,
                ft.Container(expand=True),
                ft.Row([
                    ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, color=ACCENT if self.currently_playing else MUTED, size=16),
                    self.now_playing_text,
                ], spacing=6),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10,
        )

        self.content = ft.Column([
            config_card,
            status_card,
            ft.Row([self.query_field, self.category_dropdown], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            card(self.list_column, padding=10, expand=True),
            ft.Row([self.previous_button, self.next_button], spacing=10),
        ], spacing=14, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.refresh_ui()

    def reindex_sounds(self):
        """Escanea todos los archivos de audio en la carpeta SFX configurada y los organiza por subcarpetas."""
        raw_folders = self.controller.preferences.paths.get("sfx", "")
        self._apply_sounds(*self._scan_sounds(raw_folders), raw_folders)

    @staticmethod
    def _scan_sounds(raw_folders):
        folders = [p.strip() for p in raw_folders.split(";") if p.strip()]
        
        valid_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
        sounds: list[SoundEntry] = []
        categories_count: dict[str, int] = {}

        for fld in folders:
            base_dir = Path(fld)
            if not base_dir.is_dir():
                continue
            for root, _, files in os.walk(base_dir):
                rel_dir = os.path.relpath(root, base_dir)
                cat_name = "General" if rel_dir == "." else rel_dir.split(os.sep)[0]
                for file_name in sorted(files):
                    f_path = Path(file_name)
                    ext = f_path.suffix.lower()
                    if ext in valid_exts:
                        full_p = os.path.join(root, file_name)
                        try:
                            rel_p = os.path.relpath(full_p, base_dir)
                        except ValueError:
                            rel_p = file_name
                        sound = SoundEntry(
                            id=f"usr_{len(sounds)}",
                            name=f_path.stem,
                            category=cat_name,
                            subpath=rel_p.replace("\\", "/"),
                            full_path=full_p,
                            ext=ext.upper().replace(".", ""),
                            is_procedural=False,
                        )
                        sounds.append(sound)
                        categories_count[cat_name] = categories_count.get(cat_name, 0) + 1

        # Agregar los sonidos procedurales integrados
        for asset in DEFAULT_SFX_ASSETS:
            cat_name = f"Procedural ({asset.category.capitalize()})"
            sounds.append(
                SoundEntry(
                    id=asset.id,
                    name=asset.name,
                    category=cat_name,
                    subpath=asset.relative_path,
                    full_path="",
                    ext="WAV",
                    is_procedural=True,
                )
            )
            categories_count[cat_name] = categories_count.get(cat_name, 0) + 1

        return sounds, categories_count

    def _apply_sounds(self, sounds, categories_count, raw_folders):
        self.all_sounds, self.categories = sounds, categories_count
        self._indexed_paths = raw_folders

        # Actualizar opciones del desplegable
        options = {"all": f"Todos los tipos ({len(self.all_sounds)})"}
        for cat in sorted(self.categories.keys()):
            options[cat] = f"{cat} ({self.categories[cat]})"
        self.category_dropdown.options = [ft.dropdown.Option(k, v) for k, v in options.items()]
        if self.category_dropdown.value not in options:
            self.category_dropdown.value = "all"

    async def reindex(self):
        self.offset = 0
        await self.open(force=True)
        self.app.notify(f"Catálogo SFX reindexado: {len(self.all_sounds)} sonidos cargados.")
        self.app.page.update()

    async def open(self, force=False):
        async with self._load_lock:
            raw = self.controller.preferences.paths.get('sfx', '')
            if force or raw != self._indexed_paths:
                self.status_banner.value = 'Leyendo los nombres de los efectos…'
                self.app.page.update()
                sounds, counts = await asyncio.get_running_loop().run_in_executor(
                    self.app.media_executor, self._scan_sounds, raw)
                self._apply_sounds(sounds, counts, raw)
            self.refresh_ui()

    async def on_filter_changed(self):
        self.offset = 0
        self.refresh_ui()
        self.app.page.update()

    async def paginate(self, direction):
        self.offset = max(0, self.offset + direction * PAGE_SIZE)
        self.refresh_ui()

    async def stop_audio(self):
        global_sound_player.stop()
        self.currently_playing = None
        self.now_playing_text.value = 'Ningún sonido en reproducción'
        self.now_playing_text.color = MUTED
        self.refresh_ui()

    async def go_to_library_sfx(self):
        self.app.library.category = "sfx"
        self.app.library.update_folders_ui()
        self.app.library.refresh()
        await self.app.navigate("library")

    async def toggle_play(self, sound: SoundEntry):
        """Reproduce o detiene la preescucha del sonido con un clic."""
        if not sound.full_path:
            self.app.notify(f"El sonido {sound.name} es generado de forma procedural al exportar.")
            return

        if self.currently_playing == sound.full_path:
            global_sound_player.stop()
            self.currently_playing = None
            self.now_playing_text.value = "Reproducción detenida"
            self.now_playing_text.color = MUTED
        else:
            success = global_sound_player.play(sound.full_path)
            if success:
                self.currently_playing = sound.full_path
                self.now_playing_text.value = f"▶ {sound.name}"
                self.now_playing_text.color = ACCENT
            else:
                self.app.notify(f"No se pudo reproducir: {sound.name}")
        self.refresh_ui()
        self.app.page.update()

    async def copy_sound_path(self, sound: SoundEntry):
        if sound.full_path:
            self.app.page.set_clipboard(sound.full_path)
            self.app.notify(f"Ruta copiada al portapapeles: {sound.name}")
        else:
            self.app.page.set_clipboard(sound.name)
            self.app.notify(f"Nombre copiado: {sound.name}")

    def _render_sfx_item(self, sound: SoundEntry) -> ft.Container:
        is_playing = (self.currently_playing == sound.full_path) and bool(sound.full_path)
        return ft.Container(
            content=ft.Stack([
                ft.Container(alignment=ft.Alignment.TOP_CENTER, padding=ft.Padding.only(top=22),
                    content=ft.IconButton(
                        ft.Icons.STOP_ROUNDED if is_playing else ft.Icons.PLAY_ARROW_ROUNDED,
                        icon_color=ACCENT if is_playing else TEXT, icon_size=30,
                        on_click=self.app.bind(self.toggle_play, sound),
                        tooltip='Detener' if is_playing else 'Escuchar',
                    )),
                ft.Container(left=6, top=6, content=text(sound.ext, size=9, color=MUTED)),
                ft.Container(right=0, top=0, content=ft.IconButton(
                    ft.Icons.CONTENT_COPY_ROUNDED, icon_color=MUTED, icon_size=14,
                    tooltip='Copiar ruta del archivo', on_click=self.app.bind(self.copy_sound_path, sound),
                )),
                ft.Container(left=8, right=8, bottom=8, content=ft.Column([
                    text(sound.name, size=11, weight=ft.FontWeight.W_600, color=ACCENT if is_playing else TEXT,
                         max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    text(sound.category, size=9, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=2, tight=True)),
            ], fit=ft.StackFit.EXPAND),
            tooltip=sound.subpath, border_radius=10, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor='#162822' if is_playing else '#14181B',
            border=ft.Border.all(1.5, ACCENT if is_playing else LINE),
            on_click=self.app.bind(self.toggle_play, sound),
        )

    def refresh_ui(self):
        query = self.query_field.value.strip().lower()
        selected_cat = self.category_dropdown.value

        filtered: list[SoundEntry] = []
        for sound in self.all_sounds:
            if selected_cat != "all" and sound.category != selected_cat:
                continue
            if query and (query not in sound.name.lower() and query not in sound.subpath.lower()):
                continue
            filtered.append(sound)

        total_matching = len(filtered)
        self.offset = min(self.offset, max(0, (total_matching - 1) // PAGE_SIZE * PAGE_SIZE))
        displayed = filtered[self.offset:self.offset + PAGE_SIZE]
        self.previous_button.disabled = self.offset == 0
        self.next_button.disabled = self.offset + PAGE_SIZE >= total_matching
        first = self.offset + 1 if displayed else 0
        pages = max(1, (total_matching + PAGE_SIZE - 1) // PAGE_SIZE)
        self.status_banner.value = (
            f'{first}–{self.offset + len(displayed)} de {total_matching} sonidos · '
            f'página {self.offset // PAGE_SIZE + 1}/{pages}'
        )

        if not displayed:
            empty_text = (
                f"No se encontraron efectos para '{query}' en la categoría seleccionada."
                if query or selected_cat != "all"
                else "No se detectaron efectos en la carpeta configurada. Añade archivos de audio o reindexa."
            )
            self.list_column.controls = [
                ft.Container(
                    content=text(empty_text, color=MUTED, size=12),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            ]
        else:
            self.list_column.controls = [self._render_sfx_item(s) for s in displayed]

    def refresh(self):
        if self._indexed_paths != self.controller.preferences.paths.get('sfx', ''):
            self.reindex_sounds()
        self.refresh_ui()
