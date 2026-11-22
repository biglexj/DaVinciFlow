"""Vista especializada de B-Rolls y recursos visuales complementarios."""

import asyncio
import os
from pathlib import Path
import flet as ft

from davinci_flow.assets.cover_art import sidecar_image_path
from davinci_flow.assets.broll_catalog import SUPPORTED_VIDEO_EXTENSIONS
from shared.components import ACCENT, LINE, MUTED, TEXT, button, card, field, text
from shared.inline_video import InlineVideoPreview

PAGE_SIZE = 48


class BRollsView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.video_preview = InlineVideoPreview(app)
        self.offset = 0
        self.has_next = False
        self._scan_cache = {}
        self.query = field("Buscar en B-Rolls", expand=True, on_change=self.app.bind(self.search))
        self.list_column = ft.GridView(expand=True, max_extent=240, child_aspect_ratio=16/9,
                                       spacing=10, run_spacing=10, padding=4)
        self.summary = text("Configura carpetas de B-Roll para ver tus recursos visuales.", color=MUTED, size=12)
        self.previous_button = button('Anterior', app.bind(self.paginate, -1))
        self.next_button = button('Siguiente', app.bind(self.paginate, 1))
        self.folders_card = card(
            ft.Row([
                ft.Icon(ft.Icons.VIDEO_LIBRARY_ROUNDED, color=ACCENT, size=18),
                self.summary,
                ft.Container(expand=True),
                button("Añadir carpeta", self.app.bind(self.browse_folder), ft.Icons.CREATE_NEW_FOLDER_OUTLINED),
                button("Reindexar", self.app.bind(self.reindex), ft.Icons.REFRESH, primary=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10,
        )

        self.content = ft.Column([
            self.folders_card,
            ft.Row([self.query]),
            card(self.list_column, padding=10, expand=True),
            ft.Row([self.previous_button, self.next_button], spacing=8),
        ], spacing=14, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


    async def browse_folder(self):
        await self.stop_preview()
        self.app.library.category = "visuals"
        await self.app.library.browse()
        await self.open(force=True)

    async def reindex(self):
        await self.stop_preview()
        self.app.library.category = "visuals"
        await self.app.library.scan()
        await self.open(force=True)

    async def search(self):
        await self.stop_preview()
        self.offset = 0
        await self.open()
        self.app.page.update()

    async def paginate(self, direction):
        if direction > 0 and not self.has_next:
            return
        await self.stop_preview()
        self.offset = max(0, self.offset + direction * PAGE_SIZE)
        await self.open()

    async def open(self, force=False):
        if force:
            self._scan_cache.clear()
        key = self._scan_key()
        if key not in self._scan_cache:
            self.summary.value = 'Leyendo los nombres de los clips…'
            self.app.page.update()
            files = await asyncio.get_running_loop().run_in_executor(
                self.app.media_executor, self._collect_files, *key)
            if key != self._scan_key():
                return
            self._remember(key, files)
        self.refresh()

    def _scan_key(self):
        return (self.controller.preferences.paths.get('visuals', ''),
                self.query.value.strip().lower(), self.offset)

    def _remember(self, key, files):
        if len(self._scan_cache) >= 4:
            self._scan_cache.pop(next(iter(self._scan_cache)))
        self._scan_cache[key] = files

    def _render_broll_item(self, item_path: Path):
        ext = item_path.suffix.lower()
        is_video = ext in SUPPORTED_VIDEO_EXTENSIONS
        icon = ft.Icons.MOVIE_OUTLINED if is_video else ft.Icons.IMAGE_OUTLINED
        type_label = "Vídeo" if is_video else "Imagen"
        size_mb = 0.0
        try:
            size_mb = item_path.stat().st_size / (1024 * 1024)
        except OSError:
            pass

        poster = sidecar_image_path(item_path) if is_video else None
        if not is_video or poster:
            visual = ft.Image(src=str(poster or item_path), fit=ft.BoxFit.COVER,
                              cache_width=480, error_content=ft.Icon(icon, size=34, color=MUTED))
        else:
            visual = ft.Container(ft.Icon(icon, size=34, color=MUTED), alignment=ft.Alignment.CENTER)
        host = ft.Container(content=visual) if is_video else None
        playback = []
        if is_video:
            play_button = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=TEXT, icon_size=30,
                                       tooltip='Reproducir vídeo')
            play_button.on_click = self.app.bind(self.video_preview.toggle, item_path, host, visual, play_button)
            playback = [ft.Container(content=play_button, alignment=ft.Alignment.CENTER)]
        return ft.Container(ft.Stack([
            host if is_video else visual,
            ft.Container(left=7, top=7, bgcolor='#CC101418', border_radius=4, padding=4,
                         content=text(f'{type_label} · {ext.lstrip(".").upper()}', size=10, color=TEXT)),
            ft.Container(left=0, right=0, bottom=0, padding=8,
                         gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                                                    colors=['#00101418', '#F0101418']),
                         content=ft.Column([
                             text(item_path.stem, size=12, color=TEXT, max_lines=2,
                                  overflow=ft.TextOverflow.ELLIPSIS),
                             text(f'{size_mb:.1f} MB', size=10, color=MUTED),
                         ], spacing=2, tight=True)),
            *playback,
        ], fit=ft.StackFit.EXPAND), tooltip=str(item_path), border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS, bgcolor='#14181B', border=ft.Border.all(1.5, LINE),
            on_click=play_button.on_click if is_video else None)

    async def stop_preview(self):
        await self.video_preview.stop()

    @staticmethod
    def _files(root, recursive):
        # Orden estable entre páginas, sin recorrer todo el árbol para ordenar.
        for directory, folders, files in os.walk(root):
            folders.sort(key=str.casefold)
            for name in sorted(files, key=str.casefold):
                yield Path(directory) / name
            if not recursive:
                break

    @staticmethod
    def _collect_files(raw_folders, query, offset):
        folders = [p.strip() for p in raw_folders.split(";") if p.strip()]

        matched_files = []
        limit = offset + PAGE_SIZE + 1
        valid_extensions = SUPPORTED_VIDEO_EXTENSIONS | {'.png', '.jpg', '.jpeg', '.webp'}

        for fld in folders:
            p = Path(fld)
            if not p.is_dir():
                continue
            try:
                # Si no hay búsqueda, solo listar archivos superficiales para evitar escanear terabytes de anime
                iterator = BRollsView._files(p, recursive=bool(query))
                for file_path in iterator:
                    if file_path.suffix.lower() in valid_extensions and file_path.is_file():
                        if not query or query in file_path.name.lower():
                            matched_files.append(file_path)
                            if len(matched_files) >= limit:
                                break
            except OSError:
                continue
            if len(matched_files) >= limit:
                break

        return tuple(matched_files)

    def refresh(self):
        key = self._scan_key()
        raw_folders, query, _ = key
        folders = [p.strip() for p in raw_folders.split(';') if p.strip()]
        if key not in self._scan_cache:
            self._remember(key, self._collect_files(*key))
        matched_files = self._scan_cache[key]

        if self.offset and len(matched_files) <= self.offset:
            self.offset = 0
            self._remember(self._scan_key(), matched_files)
            self.refresh()
            return
        self.has_next = len(matched_files) > self.offset + PAGE_SIZE
        matched_files = matched_files[self.offset:self.offset + PAGE_SIZE]
        self.previous_button.disabled = self.offset == 0
        self.next_button.disabled = not self.has_next
        self.summary.value = f'{len(folders)} carpetas · {len(matched_files)} recursos · página {self.offset // PAGE_SIZE + 1}'

        if not matched_files:
            empty_msg = (
                f"No se encontraron clips que coincidan con '{query}'." if query
                else ("No hay archivos visuales en la raíz de las carpetas configuradas. Usa el buscador superior para explorar subcarpetas." if folders
                      else "No hay carpetas de B-Roll añadidas. Pulsa '+ Añadir carpeta' para indexar tus clips.")
            )
            self.list_column.controls = [
                ft.Container(
                    content=text(empty_msg, color=MUTED, size=12),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            ]
        else:
            self.list_column.controls = [self._render_broll_item(f) for f in matched_files]
