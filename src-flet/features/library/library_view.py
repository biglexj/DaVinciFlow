"""Biblioteca por categorías y selección explícita de contexto."""

import asyncio
from collections import Counter
from pathlib import Path
import flet as ft

from davinci_flow.assets.cover_art import cover_art, sidecar_cover
from davinci_flow.assets.library import CATEGORIES
from davinci_flow.assets.broll_catalog import SUPPORTED_VIDEO_EXTENSIONS
from davinci_flow.editorial.model import EditorialError
from shared.components import ACCENT, LINE, MUTED, SIDE, TEXT, button, card, field, text
from shared.inline_video import InlineVideoPreview

GRID_CATEGORIES = {'visuals', 'sfx', 'music'}
GRID_PAGE = 48
LIST_PAGE = 80
TILE_SIZE = 128
TILE_CACHE = 120
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
CATEGORY_ICONS = {
    'visuals': ft.Icons.MOVIE_OUTLINED,
    'sfx': ft.Icons.GRAPHIC_EQ_ROUNDED,
    'music': ft.Icons.MUSIC_NOTE_ROUNDED,
}


class LibraryView:
    def __init__(self, app, category=None):
        self.app, self.controller = app, app.controller
        self.manage_only = category is None
        self.category, self.offset = category or 'visuals', 0
        self.category_buttons = {}
        for key, label in (CATEGORIES.items() if category is None else ()):
            self.category_buttons[key] = button(label, app.bind(self.change_category, key))
        self.folders_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
        self.query = field('Buscar en esta categoría', on_change=app.bind(self.search))
        self.list = ft.ListView(expand=True, spacing=2, padding=4)
        self.grid = ft.GridView(expand=True, spacing=10, run_spacing=10, max_extent=TILE_SIZE,
                                child_aspect_ratio=1.0, padding=4, scroll=ft.ScrollMode.AUTO)
        self.player_host = ft.Container(width=0, height=0)
        self.results = ft.Column([self.list, self.grid, self.player_host], expand=True, spacing=0)
        self.summary = text('Indexa las carpetas para ver tus recursos.', color=MUTED)
        self.notes = text('', color=MUTED, selectable=True)
        self.player = None
        self.playing_id = None
        self.is_playing = False
        self.video_preview = InlineVideoPreview(app)
        self.tiles: dict[str, tuple] = {}
        self.art_hosts = {}
        self.art_loaded = set()
        self.art_generation = 0
        self._resource_snapshot = self.controller.resources
        self.folders_card = card(ft.Column([
                text('Carpetas configuradas:', size=12, color=MUTED, weight=ft.FontWeight.W_600),
                self.folders_column,
                ft.Row([
                    button('Añadir carpeta', app.bind(self.browse), ft.Icons.CREATE_NEW_FOLDER),
                    button('Guardar e indexar', app.bind(self.scan), ft.Icons.REFRESH, primary=True),
                    button('Vaciar categoría', app.bind(self.clear_category), ft.Icons.DELETE_SWEEP_OUTLINED),
                    self.summary,
                ], wrap=True, spacing=10),
            ], spacing=10, expand=self.manage_only), expand=self.manage_only)
        if self.manage_only:
            controls = [ft.Row(list(self.category_buttons.values()), wrap=True, spacing=8, run_spacing=8),
                        self.folders_card, self.notes]
        else:
            controls = [
            ft.Row([self.summary, button('Gestionar carpetas', app.bind(self.manage_folders), ft.Icons.FOLDER_OUTLINED)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
            self.query, card(self.results, padding=8, expand=True),
            ft.Row([button('Anterior', app.bind(self.paginate, -1)), button('Siguiente', app.bind(self.paginate, 1)),
                button('Quitar selección no disponible', app.bind(self.remove_missing))], wrap=True),
            self.notes,
            text('Comparte hasta 80 recursos con la IA por nombre y categoría. Los archivos permanecen en tu equipo.',
                 size=11, color=MUTED,
                 tooltip='Los documentos se catalogan por nombre; la colocación de música, sonidos y visuals se completa en las siguientes fases.'),
            ]
        self.content = ft.Column(controls, spacing=10, expand=True,
                                 horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.update_folders_ui()
        self.refresh()

    def save_path(self):
        self.controller.save_preferences()

    def _get_folders(self) -> list[str]:
        raw = self.controller.preferences.paths.get(self.category, '')
        return [p.strip() for p in raw.split(';') if p.strip()]

    def _set_folders(self, folders: list[str]) -> None:
        self.controller.preferences.paths[self.category] = '; '.join(folders)
        self.controller.save_preferences()

    def update_folders_ui(self):
        folders = self._get_folders()
        items = []
        if not folders:
            items.append(
                text(
                    f'No hay carpetas configuradas para {CATEGORIES[self.category]}. Pulsa "+ Añadir carpeta".',
                    color=MUTED,
                    size=12,
                )
            )
        else:
            for idx, fld in enumerate(folders):
                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.FOLDER, size=16, color=ACCENT),
                            text(fld, size=12, color=TEXT, expand=True, selectable=True),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color='#FF6B6B',
                                tooltip='Quitar esta carpeta',
                                on_click=self.app.bind(self.remove_folder, idx),
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor='#14181C',
                        border=ft.Border.all(1, LINE),
                        border_radius=8,
                        padding=ft.Padding(left=10, right=6, top=2, bottom=2),
                    )
                )
        self.folders_column.controls = items
        self.folders_column.expand = self.manage_only
        self.folders_column.height = None if self.manage_only else (
            min(120, len(folders) * 48 + max(0, len(folders) - 1) * 6) if folders else 28)

    async def remove_folder(self, index: int):
        folders = self._get_folders()
        if 0 <= index < len(folders):
            folders.pop(index)
            self._set_folders(folders)
            self.update_folders_ui()
            self.app.page.update()

    async def clear_category(self):
        self._set_folders([])
        self.update_folders_ui()
        self.refresh()
        self.app.page.update()

    @property
    def page_size(self) -> int:
        return GRID_PAGE if self.category in GRID_CATEGORIES else LIST_PAGE

    def refresh(self):
        self.art_generation += 1
        if self._resource_snapshot is not self.controller.resources:
            self.tiles.clear()
            self.art_hosts.clear()
            self.art_loaded.clear()
            self._resource_snapshot = self.controller.resources
        self.grid.child_aspect_ratio = 16/9 if self.category == 'visuals' else 1.0
        self.grid.max_extent = 240 if self.category == 'visuals' else TILE_SIZE
        chosen = set(self.controller.preferences.resource_ids)
        counts = Counter(r.category for r in self.controller.resources)
        for key, control in self.category_buttons.items():
            control.style.bgcolor = '#19443D' if key == self.category else '#293136'
            control.style.color = ACCENT if key == self.category else '#EDF2F3'
        query = self.query.value.casefold()
        items = [r for r in self.controller.resources if r.category == self.category and (not query or query in r.name.casefold())]
        if self.offset >= len(items):
            self.offset = max(0, (len(items) - 1) // self.page_size * self.page_size)
        if self.manage_only:
            self.list.visible = self.grid.visible = False
        elif self.category in GRID_CATEGORIES:
            self._render_grid(items, chosen)
        else:
            self._render_list(items, chosen)
        self.summary.value = f'{counts.get(self.category, 0)} recursos · {len(chosen)}/80 compartidos · página {self.offset // self.page_size + 1}'
        if self.manage_only:
            self.summary.value = f'{len(self._get_folders())} carpetas · {counts.get(self.category, 0)} recursos indexados'
        missing = chosen - {r.id for r in self.controller.resources}
        self.notes.value = ' '.join(self.controller.diagnostics)
        if missing:
            self.notes.value += f' {len(missing)} seleccionados pendientes de localizar. Indexa su carpeta o quítalos explícitamente.'
        self.notes.visible = bool(self.notes.value.strip())

    def _render_list(self, items, chosen):
        self.list.visible, self.grid.visible = True, False
        self.list.controls = [ft.Checkbox(label=r.name, tooltip=r.path, value=r.id in chosen, active_color=ACCENT,
            on_change=self.app.bind(self.toggle, r.id)) for r in items[self.offset:self.offset + self.page_size]]

    def _render_grid(self, items, chosen):
        self.list.visible, self.grid.visible = False, True
        visible = items[self.offset:self.offset + self.page_size]
        if not visible:
            self.grid.controls = [ft.Container(content=text('Sin recursos para esta búsqueda.', color=MUTED, size=12),
                                               padding=20, alignment=ft.Alignment.CENTER)]
            return
        self.grid.controls = [self._tile(r, r.id in chosen) for r in visible]
        if hasattr(self.app.page, 'run_task') and not self.manage_only:
            self.app.page.run_task(self._hydrate_art, visible, self.art_generation)

    async def _hydrate_art(self, resources, generation):
        for resource in resources:
            if (self.app.closing or generation != self.art_generation
                    or self.app.current != self.category_key):
                return
            if resource.id in self.art_loaded:
                continue
            try:
                art = await asyncio.get_running_loop().run_in_executor(
                    self.app.media_executor, self._art, resource)
            except (OSError, ValueError):
                art = None
            if self.app.closing or generation != self.art_generation or self.app.current != self.category_key:
                return
            host = self.art_hosts.get(resource.id)
            if host is not None:
                self.art_loaded.add(resource.id)
                if art:
                    host.content = ft.Image(src=art[0], fit=ft.BoxFit.COVER, cache_width=320,
                        error_content=ft.Icon(CATEGORY_ICONS[resource.category], size=34, color=MUTED))
                    self.app.page.update()

    @property
    def category_key(self):
        return 'library' if self.manage_only else self.category if self.category == 'music' else 'library'

    def _art(self, resource):
        """Imagen de la ficha: carátula de audio, la propia imagen o el póster contiguo."""
        if resource.category == 'music':
            art = cover_art(resource.path)
            return (art.data, art.mime) if art else None
        if resource.category == 'visuals':
            path = Path(resource.path)
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                return str(path), None
            art = sidecar_cover(resource.path)
            return art
        return None

    def _tile(self, resource, selected):
        cached = self.tiles.get(resource.id)
        if cached is not None:
            self._mark(cached, selected, resource.id)
            return cached[0]
        visual = ft.Container(content=ft.Icon(CATEGORY_ICONS[self.category], size=34, color=MUTED),
                              bgcolor='#171C20', alignment=ft.Alignment.CENTER)
        self.art_hosts[resource.id] = visual
        name = Path(resource.name).name
        is_video = self.category == 'visuals' and Path(resource.path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
        video_host = ft.Container(content=visual) if is_video else None
        badge = ft.Container(content=ft.Icon(ft.Icons.CHECK_ROUNDED, size=14, color=SIDE),
                             bgcolor=ACCENT, border_radius=10, padding=ft.Padding.only(left=4, right=4, top=1, bottom=1))
        tile = ft.Container(
            content=ft.Stack([
                video_host if is_video else visual,
                ft.Container(left=6, top=6, content=ft.Container(
                    content=text(Path(resource.name).suffix.upper().replace('.', ''), size=9, weight=ft.FontWeight.W_600, color=TEXT),
                    bgcolor=ft.Colors.with_opacity(0.72, '#101418'), border_radius=4, padding=ft.Padding.symmetric(horizontal=5, vertical=1))),
                ft.Container(left=6, top=6, right=6, alignment=ft.Alignment.TOP_RIGHT, content=badge),
                ft.Container(left=0, right=0, bottom=0, padding=ft.Padding.only(left=8, right=8, top=20, bottom=8),
                             gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                                                       colors=[ft.Colors.with_opacity(0, ft.Colors.BLACK),
                                                               ft.Colors.with_opacity(0.85, ft.Colors.BLACK)]),
                             content=text(name, size=11, color='#FFFFFF', max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)),
            ], fit=ft.StackFit.EXPAND),
            bgcolor='#14181C', border_radius=10, border=ft.Border.all(1, LINE),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            tooltip=resource.path,
            on_click=self.app.bind(self.toggle, resource.id),
        )
        play_button = None
        if is_video:
            play_button = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=TEXT, icon_size=30,
                                       tooltip='Reproducir vídeo')
            play_button.on_click = self.app.bind(self.video_preview.toggle, resource.path, video_host, visual, play_button)
        elif self.category in {'music', 'sfx'}:
            play_button = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=TEXT, icon_size=30,
                                        tooltip='Escuchar', on_click=self.app.bind(self.play_audio, resource.id))
        if play_button is not None:
            tile.content.controls.insert(1, ft.Container(
                alignment=ft.Alignment.CENTER, content=play_button,
            ))
        entry = (tile, badge, play_button)
        if len(self.tiles) >= TILE_CACHE:
            removed = next(iter(self.tiles))
            self.tiles.pop(removed)
            self.art_hosts.pop(removed, None)
            self.art_loaded.discard(removed)
        self.tiles[resource.id] = entry
        self._mark(entry, selected, resource.id)
        return tile

    def _mark(self, entry, selected, identifier):
        tile, badge, play_button = entry
        tile.border = ft.Border.all(1.5, ACCENT if selected else LINE)
        badge.visible = selected
        if play_button is not None and self.category in {'music', 'sfx'}:
            active = self.is_playing and self.playing_id == identifier
            play_button.icon = ft.Icons.PAUSE_ROUNDED if active else ft.Icons.PLAY_ARROW_ROUNDED
            play_button.icon_color = ACCENT if active else TEXT
            play_button.tooltip = 'Pausar' if active else 'Escuchar'

    async def play_audio(self, identifier):
        import flet_video as ftv
        resource = next((item for item in self.controller.resources if item.id == identifier), None)
        if resource is None or not Path(resource.path).is_file():
            raise EditorialError('No se encontró el archivo de audio. Vuelve a indexar su carpeta.')
        if self.playing_id == identifier and self.player is not None:
            if self.is_playing:
                await self.player.pause()
            else:
                await self.player.play()
            self.is_playing = not self.is_playing
            self.refresh()
            return
        if self.player is not None:
            await self.player.pause()
        self.player = ftv.Video(
            playlist=[ftv.VideoMedia(Path(resource.path).as_uri())], autoplay=True, wakelock=False,
            width=0, height=0, controls=None, on_complete=self._audio_complete, on_error=self._audio_error,
            configuration=ftv.VideoConfiguration(
                enable_hardware_acceleration=False, hardware_decoding_api='no',
            ),
        )
        self.playing_id = identifier
        self.is_playing = True
        self.player_host.content = self.player
        self.refresh()

    def _audio_complete(self, event):
        if event.data is True and event.control is self.player:
            self.is_playing = False
            self.playing_id = None
            self.refresh()
            self.app.page.update()

    def _audio_error(self, event):
        if event.control is not self.player:
            return
        self.is_playing = False
        self.playing_id = None
        self.player = None
        self.player_host.content = None
        self.refresh()
        self.app.notify('No se pudo reproducir este archivo de audio.')
        self.app.page.update()

    async def stop_audio(self):
        if self.player is not None:
            try:
                await self.player.pause()
            finally:
                self.player = None
                self.playing_id = None
                self.is_playing = False
                self.player_host.content = None
                self.refresh()

    async def change_category(self, key):
        if self.category != key:
            await self.stop_preview()
        self.category, self.offset = key, 0
        self.update_folders_ui()
        self.refresh()
        self.app.page.update()

    async def manage_folders(self):
        await self.stop_preview()
        await self.app.library.change_category(self.category)
        await self.app.navigate('library')

    async def browse(self):
        path = await self.app.picker.get_directory_path(
            dialog_title=f"Añadir carpeta de {CATEGORIES[self.category]}"
        )
        if path:
            folders = self._get_folders()
            if path not in folders:
                folders.append(path)
                self._set_folders(folders)
                self.update_folders_ui()
                self.app.page.update()

    async def scan(self):
        await self.video_preview.stop()
        self.controller.save_preferences()
        result = await self.app.run('Indexando los nombres de tus recursos…', self.controller.scan_resources)
        if result:
            self.refresh()
            self.app.notify('Biblioteca indexada. Marca los recursos que podrá usar la IA.')

    async def toggle(self, identifier):
        chosen = set(self.controller.preferences.resource_ids)
        if identifier in chosen:
            chosen.remove(identifier)
        elif len(chosen) < 80:
            chosen.add(identifier)
        else:
            self.refresh()
            raise EditorialError('Elige hasta 80 recursos relevantes para esta propuesta.')
        self.controller.preferences.resource_ids = sorted(chosen)
        self.controller.save_preferences()
        self.refresh()

    async def search(self):
        await self.video_preview.stop()
        self.offset = 0
        self.refresh()

    async def paginate(self, direction):
        await self.video_preview.stop()
        self.offset = max(0, self.offset + direction * self.page_size)
        self.refresh()

    async def stop_preview(self):
        await self.video_preview.stop()
        await self.stop_audio()

    async def remove_missing(self):
        if not self.controller.library_loaded:
            raise EditorialError('Indexa primero las carpetas para comprobar los archivos disponibles.')
        available = {r.id for r in self.controller.resources}
        self.controller.preferences.resource_ids = [i for i in self.controller.preferences.resource_ids if i in available]
        self.controller.save_preferences()
        self.refresh()
