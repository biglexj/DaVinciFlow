"""Selección de títulos instalados y del proyecto en el panel central."""

from dataclasses import replace
from pathlib import Path
import flet as ft

from davinci_flow.editorial.model import EditorialError
from shared.components import ACCENT, MUTED, button, card, field, select, source_label, text


class CatalogView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.selected = {t.id for t in self.controller.templates}
        self.offset = 0
        self.query = field('Buscar títulos', expand=True, on_change=app.bind(self.search))
        self.source = select('Fuente', {'all':'Todas', 'installed':'Instalados / archivos', 'media_pool':'Proyecto · Fusion',
                            'basic':'Text+ básico'}, 'all', 200, on_select=app.bind(self.search))
        self.list = ft.ListView(height=310, spacing=4, padding=4)
        self.summary = text('', color=MUTED)
        self.detail = text('Cada capa conserva la fuente, el estilo y la animación de la plantilla que elijas.', color=MUTED)
        self.node = field('Nombre del nodo', hint_text='Vacío: detectar un único Text+', expand=True)
        self.input = field('Control de texto', 'StyledText', width=180)
        self.content = ft.Column([
            text('Tus títulos, tu estilo', 22, weight=ft.FontWeight.W_600),
            text('Elige lo que podrá usar la IA. Las composiciones de karaoke no se seleccionan automáticamente.', color=MUTED),
            ft.Row([button('Leer instalados', app.bind(self.installed), ft.Icons.DOWNLOAD_DONE),
                button('Leer proyecto', app.bind(self.project), ft.Icons.VIDEO_LIBRARY_OUTLINED),
                button('Añadir carpeta', app.bind(self.folder), ft.Icons.CREATE_NEW_FOLDER_OUTLINED)], wrap=True, run_spacing=8),
            ft.Row([self.query, self.source]),
            card(self.list, padding=8),
            ft.Row([button('Anterior', app.bind(self.paginate, -60)), button('Siguiente', app.bind(self.paginate, 60)), self.summary], wrap=True),
            ft.Row([button('Usar selección', app.bind(self.use), ft.Icons.CHECK, primary=True),
                    button('Quitar selección', app.bind(self.clear))], wrap=True),
            self.detail,
            ft.ExpansionTile(title=text('Configuración avanzada de Fusion'), controls=[
                ft.Row([self.node, self.input]), button('Asignar nodo a la selección', app.bind(self.assign_node))]),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.refresh()

    def refresh(self, sync=False):
        if sync:
            self.selected = {t.id for t in self.controller.templates}
        query, source = self.query.value.casefold(), self.source.value
        items = [t for t in sorted(self.controller.catalog.values(), key=lambda t:t.name.casefold())
                 if (not query or query in (t.name + ' ' + t.locator).casefold()) and
                 (source == 'all' or source == 'media_pool' and t.source == 'media_pool' or
                  source == 'basic' and 'basic_titles' in t.locator or
                  source == 'installed' and t.source != 'media_pool' and 'basic_titles' not in t.locator)]
        if self.offset >= len(items):
            self.offset = max(0, (len(items) - 1) // 60 * 60)
        self.list.controls = [ft.Checkbox(label=f'{t.name}   ·   {source_label(t)}',
            value=t.id in self.selected, tooltip=t.locator, active_color=ACCENT,
            on_change=self.app.bind(self.toggle, t.id)) for t in items[self.offset:self.offset+60]]
        self.summary.value = f'{len(items)} encontradas · {len(self.selected)} elegidas · página {self.offset//60+1}'

    async def toggle(self, identifier):
        if identifier in self.selected:
            self.selected.remove(identifier)
        else:
            self.selected.add(identifier)
        self.refresh()

    async def search(self):
        self.offset = 0
        self.refresh()

    async def paginate(self, offset):
        self.offset = max(0, self.offset + offset)
        self.refresh()

    async def installed(self):
        result = await self.app.run('Leyendo títulos instalados…', self.controller.scan_titles)
        if result:
            count, errors = result
            self.detail.value = f'{count} títulos encontrados. ' + ' '.join(errors)
            self.refresh()

    async def project(self):
        result = await self.app.run('Leyendo la carpeta DaVinciFlow del proyecto…', self.controller.read_project_titles)
        if result is not None:
            self.detail.value = f'{result} plantillas del proyecto disponibles. Elige solo las que correspondan a este vídeo.'
            self.refresh()

    async def folder(self):
        configured = self.controller.preferences.paths.get('titles')
        path = await self.app.picker.get_directory_path(dialog_title='Carpeta de títulos', initial_directory=configured or None)
        if path:
            self.controller.preferences.paths['titles'] = path
            self.controller.save_preferences()
            await self.app.run('Leyendo la carpeta de títulos…', lambda:self.controller.scan_titles((Path(path),)))
            self.refresh()

    async def use(self):
        self.controller.choose_templates(self.selected)
        self.app.notify(f'{len(self.selected)} plantillas elegidas para la próxima propuesta.')

    async def clear(self):
        self.selected.clear()
        self.refresh()

    async def assign_node(self):
        if not self.selected:
            raise EditorialError('Selecciona las plantillas que quieres configurar.')
        for identifier in self.selected:
            self.controller.catalog[identifier] = replace(self.controller.catalog[identifier],
                text_tool=self.node.value.strip(), text_input=self.input.value.strip() or 'StyledText')
        await self.use()
        self.detail.value = 'Configuración asignada para la próxima propuesta. Las revisiones anteriores conservan su catálogo.'
