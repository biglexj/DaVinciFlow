"""Selección de títulos instalados y del proyecto en el panel central."""

import asyncio
from dataclasses import replace
from pathlib import Path
import flet as ft

from davinci_flow.editorial.preview_capture import ensure_title_thumbnail
from davinci_flow.editorial.model import EditorialError
from davinci_flow.editorial.title_preview import read_title_preview, title_preview_kind
from shared.components import ACCENT, LINE, MUTED, button, card, field, select, source_label, text


class CatalogView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.selected = {t.id for t in self.controller.templates}
        self.offset = 0
        self.installed_loaded = False
        self.query = field('Buscar títulos', expand=True, on_change=app.bind(self.search))
        self.source = select('Categoría / Fuente', {
            'preview_video': 'Con animación',
            'preview_image': 'Con miniatura',
            'all': 'Todas las plantillas',
            'davinci_flow': 'DaVinci Flow',
            'karaoke': 'DaVinci Flow · Karaoke',
            'native': '✨ Nativos DaVinci Resolve',
            'animated': 'Referencias animadas',
            'shorts': '📱 Shorts & Reels (Bold)',
            'youtube': '🎬 YouTube Dinámico',
            'news': '📰 Noticiero & Editorial',
            'media_pool': '📁 Proyecto · Media Pool',
            'installed': '✨ Instalados · DRFX',
            'basic': 'Text+ básico',
        }, 'all', 220, on_select=app.bind(self.search))
        self.list = ft.ResponsiveRow(spacing=12, run_spacing=12, breakpoints={'xs': 0, 'sm': 480, 'md': 720, 'lg': 960})
        self.grid_images = {}
        self.preview_buttons = {}
        self.capture_attempted = set()
        self.resolve_capture_unavailable = False
        self.thumbnail_generation = 0
        self.summary = text('', color=MUTED)
        self.detail = text('Para aplicar: títulos DRB o del Media Pool. Los archivos SETTING y DRFX se pueden consultar; necesitan una base nativa preparada.', color=MUTED)
        self.node = field('Nombre del nodo', hint_text='Vacío: detectar un único Text+', expand=True)
        self.input = field('Control de texto', 'StyledText', width=180)
        self.preset_name = field('Nombre del preset', hint_text='Ej.: Narrativa horizontal', expand=True)
        self.preset_picker = select('Mis presets', {}, None, 280)
        self.refresh_presets()
        self.packs_card = card(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ACCENT, size=18),
                    text('Packs de estilo rápido (1 clic para configurar las 3 capas):', size=13, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Row([
                    button('✨ Nativos DaVinci', app.bind(self.apply_pack, 'native'), ft.Icons.AUTO_AWESOME),
                    button('📱 Shorts Bold', app.bind(self.apply_pack, 'shorts'), ft.Icons.PHONE_ANDROID),
                    button('🎬 YouTube Dinámico', app.bind(self.apply_pack, 'youtube'), ft.Icons.ONDEMAND_VIDEO),
                    button('📰 Noticiero TV', app.bind(self.apply_pack, 'news'), ft.Icons.NEWSPAPER),
                    button('✏️ Text+ Básico', app.bind(self.apply_pack, 'basic'), ft.Icons.TITLE),
                ], wrap=True, spacing=8, run_spacing=8),
            ], spacing=8),
            padding=10,
        )
        presets = ft.ExpansionTile(title=text('Mis presets'), controls=[card(ft.Column([
            text('Guarda una selección de plantillas para próximas ediciones.', color=MUTED),
            ft.Row([self.preset_picker, button('Usar preset', app.bind(self.load_preset))], wrap=True),
            ft.Row([self.preset_name, button('Guardar selección', app.bind(self.save_preset))]),
        ], spacing=10))])
        self.content = ft.Column([
            ft.Row([button('Leer instalados', app.bind(self.installed), ft.Icons.DOWNLOAD_DONE),
                    button('Leer proyecto', app.bind(self.project), ft.Icons.VIDEO_LIBRARY_OUTLINED),
                    button('Añadir carpeta', app.bind(self.folder), ft.Icons.CREATE_NEW_FOLDER_OUTLINED)], wrap=True),
            ft.Row([self.query, self.source]), presets,
            card(ft.Column([self.list], expand=True, scroll=ft.ScrollMode.AUTO), padding=8, expand=True),
            ft.Row([button('Anterior', app.bind(self.paginate, -60)), button('Siguiente', app.bind(self.paginate, 60)),
                    self.summary, button('Usar selección', app.bind(self.use), ft.Icons.CHECK, primary=True),
                    button('Quitar selección', app.bind(self.clear))], wrap=True),
            ft.ExpansionTile(title=text('Opciones de plantillas'), controls=[self.detail, self.packs_card,
                ft.Row([self.node, self.input]), button('Asignar nodo a la selección', app.bind(self.assign_node))]),
        ], spacing=10, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.refresh()

    def _render_template_item(self, template):
        picture = ft.Container(ft.Icon(ft.Icons.IMAGE_OUTLINED, color=MUTED, size=32),
                               aspect_ratio=16/9, bgcolor='#0B0E10', border_radius=7,
                               alignment=ft.Alignment.CENTER, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                               on_click=self.app.bind(self.preview, template.id))
        self.grid_images[template.id] = picture
        action = button('Ver diseño',
                        self.app.bind(self.preview, template.id), ft.Icons.PLAY_CIRCLE_OUTLINE)
        self.preview_buttons[template.id] = action
        return ft.Container(
            ft.Column([picture,
                ft.Row([ft.Checkbox(value=template.id in self.selected, active_color=ACCENT,
                                   on_change=self.app.bind(self.toggle, template.id)),
                        text(template.name, size=12, weight=ft.FontWeight.W_600, expand=True,
                             max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, tooltip=template.name)], spacing=3),
                action], spacing=7),
            col={'xs': 12, 'sm': 6, 'md': 4, 'lg': 3},
            bgcolor='#182220' if template.id in self.selected else '#14181B',
            border=ft.Border.all(1, ACCENT if template.id in self.selected else LINE),
            border_radius=9, padding=9,
            tooltip=source_label(template),
        )

    async def _hydrate_thumbnails(self, identifiers, generation):
        loop = asyncio.get_running_loop()
        for identifier in identifiers:
            if self.app.closing or self.app.current != 'catalog' or generation != self.thumbnail_generation:
                return
            template = self.controller.catalog.get(identifier)
            if template is None or identifier not in self.grid_images:
                continue
            available = None
            try:
                available = await loop.run_in_executor(self.app.media_executor, read_title_preview, template)
                if self.app.closing or self.app.current != 'catalog' or generation != self.thumbnail_generation:
                    return
                if self.resolve_capture_unavailable and not available.image and not available.video:
                    continue
                if identifier in self.capture_attempted and not available.image:
                    continue
                self.capture_attempted.add(identifier)
                path = await loop.run_in_executor(self.app.executor, ensure_title_thumbnail, template)
                if self.app.closing or self.app.current != 'catalog' or generation != self.thumbnail_generation:
                    return
                picture = self.grid_images.get(identifier)
                if picture is not None:
                    picture.content = ft.Image(src=str(path), fit='contain', expand=True)
                    picture.tooltip = 'Captura real de la plantilla'
                    self.preview_buttons[identifier].content = 'Ver animación' if available.video else 'Ver captura'
            except Exception as error:
                if available is not None and not available.image and not available.video:
                    self.resolve_capture_unavailable = True
                picture = self.grid_images.get(identifier)
                if picture is not None:
                    picture.content = text('Captura pendiente', size=11, color=MUTED)
                    picture.tooltip = str(error)
            if not self.app.closing:
                self.app.page.update()

    async def preview(self, identifier):
        template = self.controller.catalog[identifier]
        def load():
            preview = read_title_preview(template)
            if not preview.image and not preview.video:
                ensure_title_thumbnail(template)
                preview = read_title_preview(template)
            return preview
        preview = await self.app.run('Leyendo vista previa…', load)
        if preview is None:
            return

        page = self.app.page
        previous_keyboard_handler = page.on_keyboard_event

        async def restore_keyboard(event):
            if page.on_keyboard_event is on_key:
                page.on_keyboard_event = previous_keyboard_handler
                page.update()

        async def close(event):
            if dialog.open:
                dialog.open = False
                await restore_keyboard(event)

        async def on_key(event):
            if event.key in {' ', 'Space'} and not (event.ctrl or event.alt or event.meta):
                await close(event)

        async def on_video_error(event):
            if dialog.open:
                await close(event)
                self.app.show_error('No se pudo reproducir la vista previa.')

        if preview.video:
            import flet_video as ftv
            media = ftv.Video(playlist=[ftv.VideoMedia(preview.video.as_uri())],
                              autoplay=True, volume=0, playlist_mode=ftv.PlaylistMode.SINGLE,
                              width=720, height=405,
                              on_error=on_video_error)
            caption = 'Animación original incluida con la plantilla.'
        elif preview.image:
            media = ft.Image(src=str(preview.image), width=720, height=405, fit='contain')
            caption = 'Captura del diseño de la plantilla.'
        else:
            media = text('Esta plantilla no incluye una vista previa. Puedes revisar su diseño en Resolve.', size=14)
            caption = 'No se ha generado una representación de este título.'

        dialog = ft.AlertDialog(
            title=text(template.name, 18), alignment=ft.Alignment.CENTER,
            content=ft.Container(ft.Column([media, text(caption, size=12, color=MUTED)],
                                          tight=True, spacing=12), width=720),
            actions=[button('Cerrar', close)], modal=False, on_dismiss=restore_keyboard,
        )
        page.show_dialog(dialog)
        page.on_keyboard_event = on_key
        page.update()

    def refresh_presets(self):
        self.preset_picker.options = [ft.DropdownOption(name) for name in self.controller.preferences.title_presets]

    async def save_preset(self):
        count = self.controller.save_title_preset(self.preset_name.value or '', self.selected)
        self.refresh_presets()
        self.preset_picker.value = self.preset_name.value.strip()
        self.app.notify(f'Preset guardado con {count} plantillas. Disponible para próximas ediciones.')

    async def load_preset(self):
        count = self.controller.use_title_preset(self.preset_picker.value)
        self.selected = {t.id for t in self.controller.templates}
        self.refresh()
        self.app.notify(f'{count} plantillas del preset preparadas para la próxima propuesta.')

    def refresh(self, sync=False):
        self.thumbnail_generation += 1
        if sync:
            self.selected = {t.id for t in self.controller.templates}
        query, source = self.query.value.casefold(), self.source.value
        items = []
        for t in sorted(self.controller.catalog.values(), key=lambda t: (t.category not in {'davinci_flow', 'karaoke'}, t.name.casefold())):
            cat = getattr(t, 'category', '')
            if query and query not in (t.name + ' ' + t.locator + ' ' + cat).casefold():
                continue
            if source == 'all':
                items.append(t)
            elif source in {'davinci_flow', 'karaoke'} and cat == source:
                items.append(t)
            elif source == 'preview_video' and title_preview_kind(t) == 'video':
                items.append(t)
            elif source == 'preview_image' and title_preview_kind(t) == 'image':
                items.append(t)
            elif source == 'animated' and cat == 'animated':
                items.append(t)
            elif source == 'native' and (cat == 'native' or t.source == 'native' or 'templates.drfx' in t.locator.lower()):
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
        self.grid_images.clear()
        self.preview_buttons.clear()
        visible = items[self.offset:self.offset+60]
        self.list.controls = [self._render_template_item(t) for t in visible]
        if self.app.current == 'catalog' and hasattr(self.app.page, 'run_task'):
            self.app.page.run_task(self._hydrate_thumbnails, [t.id for t in visible], self.thumbnail_generation)
        self.summary.value = f'{len(items)} encontradas · {len(self.selected)} elegidas · página {self.offset//60+1}'

    async def apply_pack(self, pack_name):
        count = self.controller.choose_pack(pack_name)
        self.selected = {t.id for t in self.controller.templates}
        self.refresh()
        names = {
            'native': '✨ Nativos DaVinci Resolve',
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
            self.installed_loaded = True
            self.capture_attempted.clear()
            self.resolve_capture_unavailable = False
            self.detail.value = f'{count} títulos encontrados. Las vistas usan las muestras originales disponibles. ' + ' '.join(errors)
            self.refresh()

    async def open(self):
        if not self.installed_loaded:
            await self.installed()
        else:
            self.refresh()

    async def project(self):
        result = await self.app.run('Leyendo títulos del proyecto…', self.controller.read_project_titles)
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
