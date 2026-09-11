"""Biblioteca por categorías y selección explícita de contexto."""

from collections import Counter
from pathlib import Path
import flet as ft

from davinci_flow.assets.library import CATEGORIES
from davinci_flow.editorial.model import EditorialError
from shared.components import ACCENT, LINE, MUTED, TEXT, button, card, field, text


class LibraryView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.category, self.offset = 'visuals', 0
        self.category_buttons = {}
        for key, label in CATEGORIES.items():
            self.category_buttons[key] = button(label, app.bind(self.change_category, key))
        self.folders_column = ft.Column(spacing=6)
        self.query = field('Buscar en esta categoría', on_change=app.bind(self.search))
        self.list = ft.ListView(height=285, spacing=2, padding=4)
        self.summary = text('Indexa las carpetas para ver tus recursos.', color=MUTED)
        self.notes = text('', color=MUTED, selectable=True)
        self.content = ft.Column([
            text('Una biblioteca, cada recurso en su lugar', 22, weight=ft.FontWeight.W_600),
            text('Imágenes, vídeo, efectos, música y contexto. Tus archivos permanecen en sus carpetas.', color=MUTED),
            ft.Row(list(self.category_buttons.values()), wrap=True, spacing=8, run_spacing=8),
            card(ft.Column([
                text('Carpetas configuradas:', size=12, color=MUTED, weight=ft.FontWeight.W_600),
                self.folders_column,
                ft.Row([
                    button('Añadir carpeta', app.bind(self.browse), ft.Icons.CREATE_NEW_FOLDER),
                    button('Guardar e indexar', app.bind(self.scan), ft.Icons.REFRESH, primary=True),
                    self.summary,
                ], wrap=True, spacing=10),
            ], spacing=10)),
            self.query, card(self.list, padding=8),
            ft.Row([button('Anterior', app.bind(self.paginate, -80)), button('Siguiente', app.bind(self.paginate, 80)),
                button('Quitar selección no disponible', app.bind(self.remove_missing))], wrap=True),
            self.notes,
            text('Marca hasta 80 recursos para compartir sus nombres y categorías con la IA. No se envían los archivos. '
                 'Los documentos se catalogan por nombre; la colocación de música, sonidos y visuals se completa en las siguientes fases.', color=MUTED),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
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
                    f'No hay carpetas configuradas para {CATEGORIES[self.category].lower()}. Pulsa "+ Añadir carpeta".',
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

    async def remove_folder(self, index: int):
        folders = self._get_folders()
        if 0 <= index < len(folders):
            folders.pop(index)
            self._set_folders(folders)
            self.update_folders_ui()
            self.app.page.update()

    def refresh(self):
        chosen = set(self.controller.preferences.resource_ids)
        counts = Counter(r.category for r in self.controller.resources)
        for key, control in self.category_buttons.items():
            control.style.bgcolor = '#19443D' if key == self.category else '#293136'
            control.style.color = ACCENT if key == self.category else '#EDF2F3'
        query = self.query.value.casefold()
        items = [r for r in self.controller.resources if r.category == self.category and (not query or query in r.name.casefold())]
        if self.offset >= len(items):
            self.offset = max(0, (len(items)-1)//80*80)
        self.list.controls = [ft.Checkbox(label=r.name, tooltip=r.path, value=r.id in chosen, active_color=ACCENT,
            on_change=self.app.bind(self.toggle, r.id)) for r in items[self.offset:self.offset+80]]
        self.summary.value = f'{counts.get(self.category,0)} recursos · {len(chosen)}/80 compartidos · página {self.offset//80+1}'
        missing = chosen - {r.id for r in self.controller.resources}
        self.notes.value = ' '.join(self.controller.diagnostics)
        if missing:
            self.notes.value += f' {len(missing)} seleccionados pendientes de localizar. Indexa su carpeta o quítalos explícitamente.'

    async def change_category(self, key):
        self.category, self.offset = key, 0
        self.update_folders_ui()
        self.refresh()
        self.app.page.update()

    async def browse(self):
        path = await self.app.picker.get_directory_path(
            dialog_title=f"Añadir carpeta de {CATEGORIES[self.category].lower()}"
        )
        if path:
            folders = self._get_folders()
            if path not in folders:
                folders.append(path)
                self._set_folders(folders)
                self.update_folders_ui()
                self.app.page.update()

    async def scan(self):
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
        self.offset = 0
        self.refresh()

    async def paginate(self, offset):
        self.offset = max(0, self.offset+offset)
        self.refresh()

    async def remove_missing(self):
        if not self.controller.library_loaded:
            raise EditorialError('Indexa primero las carpetas para comprobar los archivos disponibles.')
        available = {r.id for r in self.controller.resources}
        self.controller.preferences.resource_ids = [i for i in self.controller.preferences.resource_ids if i in available]
        self.controller.save_preferences()
        self.refresh()
