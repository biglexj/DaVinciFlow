"""Selección de títulos instalados y del proyecto en el panel central."""

from dataclasses import replace
from pathlib import Path
import flet as ft

from davinci_flow.editorial.model import EditorialError
from shared.components import ACCENT, LINE, MUTED, button, card, field, select, source_label, text


class CatalogView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.selected = {t.id for t in self.controller.templates}
        self.offset = 0
        self.query = field('Buscar títulos', expand=True, on_change=app.bind(self.search))
        self.source = select('Categoría / Fuente', {
            'all': 'Todas las plantillas',
            'shorts': '📱 Shorts & Reels (Bold)',
            'youtube': '🎬 YouTube Dinámico',
            'news': '📰 Noticiero & Editorial',
            'media_pool': '📁 Proyecto · Media Pool',
            'installed': '✨ Instalados · DRFX',
            'basic': 'Text+ básico',
        }, 'all', 220, on_select=app.bind(self.search))
        self.list = ft.Column(spacing=6)
        self.summary = text('', color=MUTED)
        self.detail = text('Cada capa conserva la fuente, el estilo y la animación de la plantilla que elijas.', color=MUTED)
        self.node = field('Nombre del nodo', hint_text='Vacío: detectar un único Text+', expand=True)
        self.input = field('Control de texto', 'StyledText', width=180)
        self.packs_card = card(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ACCENT, size=18),
                    text('Packs de estilo rápido (1 clic para configurar las 3 capas):', size=13, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Row([
                    button('📱 Shorts Bold', app.bind(self.apply_pack, 'shorts'), ft.Icons.PHONE_ANDROID),
                    button('🎬 YouTube Dinámico', app.bind(self.apply_pack, 'youtube'), ft.Icons.ONDEMAND_VIDEO),
                    button('📰 Noticiero TV', app.bind(self.apply_pack, 'news'), ft.Icons.NEWSPAPER),
                    button('✏️ Text+ Básico', app.bind(self.apply_pack, 'basic'), ft.Icons.TITLE),
                ], wrap=True, spacing=8, run_spacing=8),
            ], spacing=8),
            padding=10,
        )
        self.content = ft.Column([
            text('Tus títulos, tu estilo', 22, weight=ft.FontWeight.W_600),
            text('Elige lo que podrá usar la IA o activa un pack predeterminado para tu formato.', color=MUTED),
            self.packs_card,
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

    def _render_template_item(self, t):
        is_selected = t.id in self.selected
        cat = getattr(t, 'category', '')
        name_lower = t.name.lower()

        if 'énfasis' in name_lower or 'enfasis' in name_lower or 'accent' in name_lower:
            role_label = 'Énfasis'
            role_badge_bg = '#332600'
            role_badge_border = '#8A6D00'
            preview_color = '#FFBC00'
            preview_weight = ft.FontWeight.W_800
            preview_sample = 'PALABRA DESTACADA'
        elif 'contexto' in name_lower or 'context' in name_lower:
            role_label = 'Contexto'
            role_badge_bg = '#142028'
            role_badge_border = '#243A4A'
            preview_color = '#8FA8B8'
            preview_weight = ft.FontWeight.W_400
            preview_sample = 'Línea de contexto superior'
        else:
            role_label = 'Principal'
            role_badge_bg = '#1F2A28'
            role_badge_border = '#2C4A42'
            preview_color = '#FFFFFF'
            preview_weight = ft.FontWeight.BOLD
            preview_sample = 'TEXTO PRINCIPAL'

        font_hint = "Montserrat" if ("shorts" in cat or "youtube" in cat or "bold" in name_lower) else "TextPlus"

        return ft.Container(
            content=ft.Row([
                ft.Checkbox(
                    value=is_selected,
                    active_color=ACCENT,
                    on_change=self.app.bind(self.toggle, t.id),
                ),
                ft.Column([
                    ft.Row([
                        text(t.name, size=13, weight=ft.FontWeight.W_600),
                        ft.Container(
                            content=text(source_label(t), size=10, weight=ft.FontWeight.W_500, color=ACCENT),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=10,
                            bgcolor='#172A24',
                            border=ft.Border.all(0.6, ACCENT),
                        ),
                        ft.Container(
                            content=text(role_label, size=10, weight=ft.FontWeight.W_500, color=preview_color),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=10,
                            bgcolor=role_badge_bg,
                            border=ft.Border.all(0.6, role_badge_border),
                        ),
                    ], spacing=8, alignment=ft.MainAxisAlignment.START),
                    text(f'Nodo: {t.text_tool or "TextPlus"} · Fuente sugerida: {font_hint} · Control: {t.text_input}',
                         size=11, color=MUTED),
                ], spacing=3, expand=True),
                ft.Container(
                    content=text(preview_sample, size=12, weight=preview_weight, color=preview_color),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor='#111518',
                    border=ft.Border.all(0.8, LINE),
                    border_radius=6,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor='#182220' if is_selected else '#14181B',
            border=ft.Border.all(1, ACCENT if is_selected else LINE),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        )

    def refresh(self, sync=False):
        if sync:
            self.selected = {t.id for t in self.controller.templates}
        query, source = self.query.value.casefold(), self.source.value
        items = []
        for t in sorted(self.controller.catalog.values(), key=lambda t: t.name.casefold()):
            cat = getattr(t, 'category', '')
            if query and query not in (t.name + ' ' + t.locator + ' ' + cat).casefold():
                continue
            if source == 'all':
                items.append(t)
            elif source == 'shorts' and (cat == 'shorts' or 'short' in t.name.lower()):
                items.append(t)
            elif source == 'youtube' and (cat == 'youtube' or 'youtube' in t.name.lower()):
                items.append(t)
            elif source == 'news' and (cat == 'news' or 'noticiero' in t.name.lower()):
                items.append(t)
            elif source == 'media_pool' and t.source == 'media_pool':
                items.append(t)
            elif source == 'basic' and (cat == 'basic' or 'basic_titles' in t.locator):
                items.append(t)
            elif source == 'installed' and t.source != 'media_pool' and 'basic_titles' not in t.locator:
                items.append(t)
        if self.offset >= len(items):
            self.offset = max(0, (len(items) - 1) // 60 * 60)
        self.list.controls = [self._render_template_item(t) for t in items[self.offset:self.offset+60]]
        self.summary.value = f'{len(items)} encontradas · {len(self.selected)} elegidas · página {self.offset//60+1}'

    async def apply_pack(self, pack_name):
        count = self.controller.choose_pack(pack_name)
        self.selected = {t.id for t in self.controller.templates}
        self.refresh()
        names = {
            'shorts': '📱 Shorts Bold (Viral / Alto Impacto)',
            'youtube': '🎬 YouTube Dinámico (Elegante)',
            'news': '📰 Noticiero TV (Informativo)',
            'basic': '✏️ Text+ Básico',
        }
        pack_label = names.get(pack_name, pack_name)
        self.app.notify(f'Pack {pack_label} aplicado ({count} plantillas elegidas).')


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
