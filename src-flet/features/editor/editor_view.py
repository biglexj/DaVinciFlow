import asyncio
import flet as ft

from davinci_flow.ai.model_catalog import capability_for
from davinci_flow.editorial.batch_run import (
    BATCH_CHOICES,
    EditorialBatchRun,
    EditorialBatchStore,
    capture_full_sequence,
    generate_next_batch,
)
from davinci_flow.editorial.model import EditorialConflictError, EditorialError
from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS
from shared.components import (
    ACCENT, CARD, LINE, MUTED, TEXT, MODES, FORMATS, DENSITIES, TRACK_MODES, button, card, field, scroll_table, select, text,
)


class EditorView:
    def __init__(self, app):
        self.app = app
        self.controller = app.controller
        p = self.controller.preferences
        self.selected = None
        self.conflict_cue_indices = {}
        self.track = field('Pista', '1', 72)

        self.fps = field('FPS SRT', '24', 90)
        self.first = field('Desde', '1', 80)
        self.last = field('Hasta', '120', 80)
        self.batch_size = select('Tamaño de tanda', {
            '20': '20 subtítulos',
            '50': '50 subtítulos',
            '100': '100 subtítulos',
            '500': '500 subtítulos',
            'all': 'Todo en una petición',
        }, getattr(p, 'batch_size', '20'), 190)
        self.batch_run: EditorialBatchRun | None = None
        self.batch_progress = text('Sin avance por tandas', color=MUTED)
        self.mode = select('Modo', MODES, p.mode, 190)
        self.format = select('Formato', FORMATS, p.format, 180)
        self.density = select('Densidad', DENSITIES, p.density, 160)
        self.track_mode = select('Pistas de texto', TRACK_MODES, getattr(p, 'track_mode', 'triple'), 220)
        self.direction = field('Dirección creativa', p.direction, width=340,
                               hint_text='Pocas palabras grandes; alternar con planos sin texto.', multiline=False)

        self.source_summary = text('Captura los subtítulos de tu montaje o abre un SRT.', color=MUTED)
        self.count = text('Sin fuente', color=MUTED)
        self.stage_container = ft.Container(padding=ft.Padding.only(bottom=4))
        self.table = ft.DataTable(columns=[ft.DataColumn(label=text(t, color=MUTED)) for t in
            ('Tiempo', 'Contexto', 'Principal', 'Énfasis', 'Sonido', 'Plantilla', 'Revisión')],
            rows=[], heading_row_height=38, data_row_min_height=40, data_row_max_height=44,
            column_spacing=18, horizontal_margin=14, show_checkbox_column=False,
            bgcolor=CARD, data_row_color=CARD,
            heading_row_color='#242C30', divider_thickness=0.4)
        self.empty = card(ft.Column([ft.Icon(ft.Icons.SUBTITLES_OUTLINED, color=ACCENT, size=32),
            text('Las ideas empiezan con tu montaje', size=17, weight=ft.FontWeight.W_500),
            text('Lee una pista de Resolve o importa un SRT. Después decide qué merece aparecer en pantalla.', color=MUTED)],
            spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=36)
        self.initial_loading = ft.Container(
            ft.Column([
                ft.ProgressRing(width=25, height=25, stroke_width=2.2, color=ACCENT),
                text('Cargando subtítulos…', color=MUTED),
            ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.Alignment.CENTER,
            expand=True,
            visible=False,
        )
        self.table_view = scroll_table(self.table, width=1180, height=None, expand=True)
        self.table_view.visible = False
        self.original = text('', size=13, selectable=True)
        self.reason = text('', color=MUTED, selectable=True)
        self.visual = text('', color=MUTED, selectable=True)
        self.texts, self.templates = {}, {}
        rows = []
        for role, label in (('context', 'Contexto'), ('main', 'Principal'), ('accent', 'Énfasis')):
            self.texts[role] = field(label, col={'xs':12, 'md':8})
            self.templates[role] = select('Plantilla', {}, width=None, col={'xs':12, 'md':4})
            rows.append(ft.ResponsiveRow([self.texts[role], self.templates[role]], spacing=10, run_spacing=8))
        self.sfx = select('Efecto de sonido (SFX)', {}, width=None, col={'xs':12, 'md':12})
        rows.append(ft.ResponsiveRow([self.sfx], spacing=10, run_spacing=8))
        self.enabled = ft.Checkbox(label='Mostrar texto', value=True, active_color=ACCENT)
        self.note = field('Nota si reescribes el original', expand=True)
        self.review_card = card(ft.Column([
            ft.Row([
                text('Revisar composición', 15, weight=ft.FontWeight.W_600),
                ft.Row([
                    self.enabled,
                    ft.IconButton(ft.Icons.CLOSE, tooltip='Cerrar revisión', on_click=app.bind(self.close_review), icon_size=20),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.original, self.reason, self.visual, *rows,
            self.note,
            ft.Row([
                button('Guardar revisión', app.bind(self.review), ft.Icons.CHECK, primary=True),
                button('Siguiente bloque', app.bind(self.next_block), ft.Icons.ARROW_FORWARD),
                button('Cerrar', app.bind(self.close_review), ft.Icons.CLOSE_ROUNDED),
            ], wrap=True, spacing=8),
        ], spacing=10), visible=False)
        self.user_stage = None
        self.stage_container.content = self._stage_indicator(1)
        self.content = ft.Column([
            self.stage_container,
            card(ft.Column([
                ft.Row([self.track, self.fps, self.first, self.last,
                    button('Capturar Resolve', app.bind(self.capture), ft.Icons.VIDEO_LIBRARY_OUTLINED),
                    button('Capturar pista completa', app.bind(self.capture_full), ft.Icons.SUBTITLES_OUTLINED,
                           tooltip='Captura todos los subtítulos de la pista activa y conserva propuestas previas compatibles'),
                    button('◀ Bloque ant.', app.bind(self.prev_block_range), ft.Icons.NAVIGATE_BEFORE_ROUNDED, tooltip='Retroceder y cargar el bloque anterior de subtítulos'),
                    button('Bloque sig. ▶', app.bind(self.next_block_range), ft.Icons.NAVIGATE_NEXT_ROUNDED, tooltip='Avanzar y capturar el siguiente bloque de subtítulos en Resolve'),
                    button('Cargar SRT', app.bind(self.open_srt), ft.Icons.UPLOAD_FILE_OUTLINED)], wrap=True, spacing=8, run_spacing=10),
                self.source_summary,
            ], spacing=10)),
            ft.Row([self.mode, self.format, self.density, self.track_mode], wrap=True, spacing=10, run_spacing=10),
            ft.Row([
                self.direction,
                self.batch_size,
                button('Generar tanda', app.bind(self.generate_batch), ft.Icons.AUTO_AWESOME, primary=True),
                button('Completar secuencia', app.bind(self.generate_all), ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED,
                       tooltip='Procesa y guarda cada tanda hasta terminar todos los subtítulos'),
                button('Abrir propuesta', app.bind(self.load), ft.Icons.FOLDER_OPEN),
                button('Guardar', app.bind(self.save), ft.Icons.SAVE_OUTLINED),
                button('Aprobar todo', app.bind(self.approve_all), ft.Icons.DONE_ALL,
                       tooltip='Aprobar todos los bloques de la propuesta actual'),
            ], spacing=8, run_spacing=8, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                self.count,
                self.batch_progress,
                ft.Row([
                    button('Aplicar revisión', app.bind(self.apply), ft.Icons.PLAY_ARROW_ROUNDED, primary=True,
                           tooltip='Se aplica la revisión guardada, sin volver a llamar a la IA.'),
                    button('Deshacer', app.bind(self.undo), ft.Icons.UNDO_ROUNDED,
                           tooltip='Deshacer la muestra aplicada en esta secuencia'),
                    button('Limpiar', app.bind(self.clean_tracks), ft.Icons.CLEANING_SERVICES_OUTLINED,
                           tooltip='Vaciar las pistas de DaVinci Flow (DF_CONTEXT, DF_MAIN, DF_ACCENT, DF_SFX) en Resolve'),
                ], wrap=True, spacing=8, run_spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               run_spacing=8, wrap=True),
            self.empty, self.initial_loading, self.table_view, self.review_card,
        ], spacing=10, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _stage_indicator(self, stage: int):
        stages = [
            (1, "1. Montaje y Subtítulos", ft.Icons.DOWNLOAD_ROUNDED),
            (2, "2. Mesa de Revisión", ft.Icons.RATE_REVIEW_ROUNDED),
            (3, "3. Aplicación en Resolve", ft.Icons.MOVIE_CREATION_ROUNDED),
        ]
        chips = []
        for num, label, icon in stages:
            is_current = (num == stage)
            is_past = (num < stage)
            bg = '#1F4037' if is_current else ('#162320' if is_past else '#1A2126')
            border_c = ACCENT if is_current else ('#2A4A43' if is_past else '#2B353B')
            txt_c = '#FFFFFF' if is_current else (TEXT if is_past else MUTED)
            ic_c = ACCENT if (is_current or is_past) else MUTED
            chips.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, size=14, color=ic_c),
                        text(label, size=12, weight=ft.FontWeight.W_600 if is_current else ft.FontWeight.NORMAL, color=txt_c),
                    ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    border_radius=16,
                    bgcolor=bg,
                    border=ft.Border.all(0.8, border_c),
                    ink=True,
                    tooltip=f'Cambiar a etapa: {label}',
                    on_click=self.app.bind(self.set_stage, num),
                )
            )
        return ft.Row(chips, spacing=10, alignment=ft.MainAxisAlignment.START)

    async def set_stage(self, stage: int):
        if stage == 1:
            self.user_stage = 1
            self.refresh()
            self.app.notify('Fase 1: Configuración de captura y dirección creativa.')
        elif stage == 2:
            if self.controller.snapshot is None:
                self.app.notify('Captura primero los subtítulos de Resolve o carga un SRT.')
                return
            if self.controller.proposal is None:
                self.controller.create_default_proposal()
                self.app.notify('Propuesta creada desde tus subtítulos para revisión directa.')
            self.user_stage = 2
            self.refresh()
            self.app.notify('Fase 2: Mesa de revisión de textos, estilos y sonido.')
        elif stage == 3:
            if self.controller.snapshot is None:
                self.app.notify('Captura primero una secuencia antes de aplicar.')
                return
            if self.batch_run is not None and not self.batch_run.complete:
                self.app.notify('Completa todas las tandas antes de pasar a la aplicación en Resolve.')
                return
            if self.controller.proposal is None:
                self.app.notify('Genera o revisa una propuesta antes de aplicar en Resolve.')
                return
            self.user_stage = 3
            self.refresh()
            self.app.notify('Fase 3: Verificación final y aplicación en Resolve.')

    def sync_preferences(self):
        p = self.controller.preferences
        p.mode, p.format, p.density, p.direction = self.mode.value, self.format.value, self.density.value, self.direction.value.strip()
        p.track_mode = self.track_mode.value or 'triple'
        p.batch_size = self.batch_size.value if self.batch_size.value in BATCH_CHOICES else '20'


    def refresh(self):
        snapshot, proposal = self.controller.snapshot, self.controller.proposal
        self.table.rows.clear()
        self.empty.visible = snapshot is None
        self.table_view.visible = snapshot is not None

        stage = self.user_stage
        if stage is None:
            stage = 1
            if snapshot is not None:
                if proposal is not None:
                    reviewed = sum(d.reviewed for d in proposal.decisions)
                    if reviewed == len(proposal.decisions) and len(proposal.decisions) > 0:
                        stage = 3
                    else:
                        stage = 2
                else:
                    stage = 1
        self.stage_container.content = self._stage_indicator(stage)

        if snapshot is None:
            return
        cuts_count = len(snapshot.cuts) if snapshot.cuts else 0
        cuts_str = f" · {cuts_count} cortes" if cuts_count > 0 else ""
        montage_type = "Montaje avanzado" if cuts_count > 0 else "Secuencia"
        batch_suffix = (f' · avance de secuencia: {self.batch_run.processed}/{self.batch_run.total}'
                        if self.batch_run is not None else '')
        self.source_summary.value = f'{montage_type}: {snapshot.timeline} · {len(snapshot.cues)} subtítulos{cuts_str}{batch_suffix} · {snapshot.width} × {snapshot.height} · {snapshot.fps:g} fps'
        catalog = {t.id: t.name for t in proposal.templates} if proposal else {}
        sfx_names = {a.id: a.name for a in DEFAULT_SFX_ASSETS}
        if proposal and proposal.options and getattr(proposal.options, 'resources', None):
            for r in getattr(proposal.options, 'resources', ()):
                if r.get('category') == 'sfx':
                    sfx_names[r['id']] = r['name']

        for i, cue in enumerate(snapshot.cues):
            decision = proposal.decisions[i] if proposal else None
            conflict = self.conflict_cue_indices.get(i)
            sfx_label = sfx_names.get(decision.resource_id, decision.resource_id) if (decision and decision.resource_id) else ''
            values = (f'{cue.start_frame:g}–{cue.end_frame:g}', decision.context if decision else '',
                      (decision.main if decision.enabled else 'Sin rótulo') if decision else cue.text,
                      decision.accent if decision else '',
                      sfx_label,
                      ', '.join(dict.fromkeys(catalog.get(t, '') for t in decision.templates.values())) if decision else 'Por elegir',
                      ('Revisado' if decision.reviewed else 'Pendiente') if decision else 'Fuente')
            row_bg = '#3B1818' if conflict else ('#173A35' if i == self.selected else CARD)
            text_color = '#EF4444' if conflict else (MUTED if decision and not decision.enabled else TEXT)
            cells = []
            for col_idx, (value, width) in enumerate(zip(values, (110, 130, 230, 130, 120, 170, 90))):
                display_val = value or '—'
                if conflict and col_idx == 0:
                    display_val = f'⚠️ {display_val}'
                cell_tooltip = f"[CONFLICTO con '{conflict.clip_name}' en pista {conflict.track_name} (f. {conflict.start_frame:g}–{conflict.end_frame:g})]\n" if conflict else ""
                cell_tooltip += str(value or '')
                cells.append(ft.DataCell(ft.Container(content=text(
                    display_val,
                    color=text_color,
                    weight=ft.FontWeight.BOLD if conflict else ft.FontWeight.NORMAL,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=cell_tooltip,
                ), width=width)))
            self.table.rows.append(ft.DataRow(cells=cells, selected=i == self.selected,
                color=row_bg, on_select_change=self.app.bind(self.choose, i)))
        reviewed = sum(d.reviewed for d in proposal.decisions) if proposal else 0
        active = sum(d.enabled for d in proposal.decisions) if proposal else 0
        self.count.value = f'{active} rótulos · {reviewed}/{len(snapshot.cues)} revisados' if proposal else f'{len(snapshot.cues)} subtítulos originales'
        if self.batch_run is None:
            self.batch_progress.value = 'Sin avance por tandas'
        else:
            next_number = self.batch_run.next_subtitle_number
            suffix = f' · siguiente #{next_number}' if next_number is not None else ' · secuencia completa'
            self.batch_progress.value = (
                f'{self.batch_run.processed}/{self.batch_run.total} subtítulos procesados{suffix}'
            )
        self.app.refresh_identity()

    def form_changed(self):
        p = self.controller.proposal
        if p is None or self.selected is None:
            return False
        d = p.decisions[self.selected]
        return (any(f.value.strip() != getattr(d, role).strip() for role, f in self.texts.items())
                or self.enabled.value != d.enabled or self.note.value.strip() != d.edit_note
                or any(self.templates[r].value != tid for r, tid in d.templates.items())
                or (self.sfx.value or '') != (d.resource_id or ''))

    async def replacement_allowed(self):
        if self.form_changed() or self.controller.dirty:
            return await self.app.confirm('Cambios sin guardar', 'Esta acción sustituirá la propuesta actual. ¿Continuar sin guardarla?')
        return True

    async def capture(self):
        if not await self.replacement_allowed():
            return
        track, first, last = int(self.track.value), int(self.first.value), int(self.last.value)
        result = await self.app.run('Leyendo subtítulos de Resolve…', lambda: self.controller.read_resolve(track, first, last))
        if result:
            self.batch_run = None
            self.selected = None
            self.review_card.visible = False
            self.user_stage = None
            self.refresh()
            self.app.notify('Fuente capturada. Elige la dirección creativa y genera una propuesta.')

    def _capture_or_reuse_batch(self, track: int):
        source = self.controller.snapshot
        seed = self.controller.proposal
        templates = tuple(self.controller.templates)
        if self.batch_run is not None and self.batch_run.snapshot.source == 'srt':
            snapshot = self.batch_run.snapshot
        elif source is None or source.source == 'resolve':
            snapshot, captured_templates = capture_full_sequence(track)
            if not templates:
                templates = captured_templates
        else:
            snapshot = source
        options = self.controller.options()
        return EditorialBatchStore().create_or_resume(snapshot, templates, options, seed)

    def _show_batch_run(self, run: EditorialBatchRun):
        self.batch_run = run
        prefix_end = run.next_index if run.next_index is not None else run.total
        if run.complete:
            proposal = run.proposal()
            self.controller.snapshot = run.snapshot
            self.controller.proposal = proposal
        elif prefix_end:
            proposal = run.batch_proposal(0, prefix_end, self.controller.preferences.model)
            self.controller.snapshot = proposal.snapshot
            self.controller.proposal = proposal
        else:
            self.controller.snapshot = run.snapshot
            self.controller.proposal = None
        self.controller.templates = run.templates
        self.controller.dirty = self.controller.proposal is not None
        self.selected = None
        self.review_card.visible = False
        self.user_stage = 2 if self.controller.proposal else 1
        self.refresh()

    def _persist_visible_batch_review(self):
        if self.batch_run is not None and self.controller.proposal is not None:
            self.batch_run.merge_visible_proposal(self.controller.proposal)
            EditorialBatchStore().save(self.batch_run)

    def _batch_generator_args(self):
        preferences = self.controller.preferences
        settings = getattr(self.app, 'settings', None)
        capabilities = getattr(settings, 'capabilities', ()) if settings is not None else ()
        long_context_enabled = bool(getattr(preferences, 'long_context_enabled', False))
        capability = capability_for(preferences.provider, preferences.model, capabilities)
        if long_context_enabled and not (capability.long_context and capability.supports_structured_output):
            raise EditorialError(
                'El modelo seleccionado no tiene un límite de contexto largo verificado y salida estructurada. '
                'Elige otro modelo en Ajustes o desactiva esa opción.'
            )
        return (
            preferences.batch_size,
            preferences.provider,
            preferences.model,
            long_context_enabled,
            capability,
        )

    async def capture_full(self):
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque antes de capturar toda la pista.')
        self.sync_preferences()
        self.controller.save_preferences()
        track = int(self.track.value)
        result = await self.app.run('Capturando toda la pista de subtítulos y buscando avances…',
                                    lambda: self._capture_or_reuse_batch(track), reraise=True)
        if result:
            run, message = result
            self._show_batch_run(run)
            self.app.notify(message or f'Pista completa capturada: {run.total} subtítulos.')

    async def _prepare_batch(self):
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque antes de procesar otra tanda.')
        self.sync_preferences()
        self.controller.save_preferences()
        track = int(self.track.value)
        result = await self.app.run('Capturando la secuencia completa y reanudando el avance…',
                                    lambda: self._capture_or_reuse_batch(track), reraise=True)
        if not result:
            return False
        run, message = result
        self._show_batch_run(run)
        if message:
            self.app.notify(message)
        return True

    async def generate_batch(self):
        if not await self._prepare_batch():
            return
        run = self.batch_run
        if run is None:
            return
        batch_size, provider, model, long_context_enabled, capability = self._batch_generator_args()
        next_number = run.next_subtitle_number
        if next_number is None:
            self.app.notify('La secuencia ya está completa; puedes revisar y aplicar la propuesta.')
            return
        result = await self.app.run(
            f'Generando subtítulos desde #{next_number}…',
            lambda: generate_next_batch(run, batch_size, provider, model,
                                        long_context_enabled, capability),
            reraise=True,
        )
        if result:
            start, end, _ = result
            self._show_batch_run(run)
            self.app.notify(
                f'Tanda guardada: subtítulos {run.snapshot.first + start}–{run.snapshot.first + end - 1}. '
                f'Avance {run.processed}/{run.total}.'
            )

    async def generate_all(self):
        if not await self._prepare_batch():
            return
        run = self.batch_run
        if run is None:
            return
        batch_size, provider, model, long_context_enabled, capability = self._batch_generator_args()
        while not run.complete:
            next_number = run.next_subtitle_number
            result = await self.app.run(
                f'Procesando la secuencia: empieza en #{next_number}…',
                lambda: generate_next_batch(run, batch_size, provider, model,
                                            long_context_enabled, capability),
                reraise=True,
            )
            if not result:
                break
            self._show_batch_run(run)
            self.app.page.update()
        if run.complete:
            self.app.notify(f'Secuencia completa: {run.total} subtítulos procesados y guardados. Revisa la propuesta antes de aplicar.')

    async def next_block_range(self):
        if not await self.replacement_allowed():
            return
        try:
            first = int(self.first.value)
            last = int(self.last.value)
            size = max(1, last - first + 1)
        except ValueError:
            first, last, size = 1, 120, 120
        self.first.value = str(last + 1)
        self.last.value = str(last + size)
        self.app.page.update()
        await self.capture()

    async def prev_block_range(self):
        if not await self.replacement_allowed():
            return
        try:
            first = int(self.first.value)
            last = int(self.last.value)
            size = max(1, last - first + 1)
        except ValueError:
            first, last, size = 1, 120, 120
        new_last = max(1, first - 1)
        new_first = max(1, new_last - size + 1)
        if new_last <= 1 and first <= 1:
            self.app.notify('Ya te encuentras en el primer bloque de subtítulos.')
            return
        self.first.value = str(new_first)
        self.last.value = str(new_last)
        self.app.page.update()
        await self.capture()

    async def open_srt(self):
        if not await self.replacement_allowed():
            return
        path = await self.app.pick_file('Abrir subtítulos', ['srt'])
        if path:
            self.controller.read_srt(path, float(self.fps.value))
            self.batch_run = None
            self.selected = None
            self.review_card.visible = False
            self.user_stage = None
            self.refresh()

    async def generate(self):
        if not await self.replacement_allowed():
            return
        self.sync_preferences()
        result = await self.app.run('La IA está preparando tu propuesta…', self.controller.generate)
        if result:
            self.selected = None
            self.review_card.visible = False
            self.user_stage = 2
            self.refresh()
            self.app.notify('Propuesta lista. Revisa cada bloque, incluidos los momentos sin texto.')

    async def choose(self, index):
        if self.controller.proposal is None:
            self.controller.create_default_proposal()
            self.user_stage = 2
            self.app.notify('Propuesta inicial creada desde tus subtítulos para revisión directa.')
        if self.selected == index:
            await self.close_review()
            return
        if self.form_changed():
            raise EditorialError('Guarda la revisión del bloque antes de cambiar de fila.')
        self.selected = index
        self.user_stage = 2
        p = self.controller.proposal
        if p is None:
            return
        d = p.decisions[index]
        for role in self.texts:
            self.texts[role].value = getattr(d, role)
            self.templates[role].options = [ft.DropdownOption(key=t.id, text=t.name) for t in p.templates]
            self.templates[role].value = d.templates.get(role)
        sfx_options = [ft.DropdownOption(key='', text='(Sin sonido)')]
        sfx_options.extend([ft.DropdownOption(key=a.id, text=f'{a.name} ({a.category})') for a in DEFAULT_SFX_ASSETS])
        if p.options and getattr(p.options, 'resources', None):
            seen_keys = {opt.key for opt in sfx_options}
            for r in getattr(p.options, 'resources', ()):
                if r.get('category') == 'sfx' and r['id'] not in seen_keys:
                    sfx_options.append(ft.DropdownOption(key=r['id'], text=r['name']))
        self.sfx.options = sfx_options
        self.sfx.value = d.resource_id or ''
        self.enabled.value, self.note.value = d.enabled, d.edit_note
        self.original.value = f'Original: {p.snapshot.cues[index].text}'
        self.reason.value = d.reason
        self.visual.value = f'Imagen sugerida: {d.visual_note}' if d.visual_note else ''
        self.visual.visible = bool(d.visual_note)
        self.review_card.visible = True
        self.refresh()

    async def review(self):
        if self.selected is None:
            return
        texts = {r: f.value.strip() for r, f in self.texts.items()}
        assigned = {r: self.templates[r].value or '' for r, v in texts.items() if v}
        sfx_val = (self.sfx.value or '').strip()
        self.controller.review(self.selected, **texts, templates=assigned,
                               resource_id=sfx_val,
                               enabled=bool(self.enabled.value), edit_note=self.note.value.strip())
        self._persist_visible_batch_review()
        self.refresh()
        self.app.notify('Revisión del bloque guardada en la propuesta.')

    async def close_review(self):
        if self.form_changed():
            if not await self.app.confirm('Cambios sin guardar', 'Has modificado este bloque. ¿Deseas salir sin guardar los cambios?'):
                return
        self.selected = None
        self.review_card.visible = False
        self.refresh()

    async def next_block(self):
        if self.selected is not None and self.selected + 1 < len(self.controller.snapshot.cues):
            await self.choose(self.selected + 1)

    async def load(self):
        if not await self.replacement_allowed():
            return
        path = await self.app.pick_file('Abrir propuesta editorial', ['json'])
        if path:
            self.controller.load_proposal(path)
            self.batch_run = None
            p = self.controller.preferences
            self.mode.value, self.format.value, self.density.value = p.mode, p.format, p.density
            self.track_mode.value = getattr(p, 'track_mode', 'triple')
            self.direction.value = p.direction

            self.selected = None
            self.review_card.visible = False
            self.refresh()
            self.app.catalog.refresh(sync=True)
            self.app.settings.refresh()

    async def save(self):
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque que estás editando.')
        if self.controller.proposal is None:
            raise EditorialError('Todavía no hay propuesta para guardar.')
        path = await self.app.picker.save_file(dialog_title='Guardar propuesta', file_name='propuesta-editorial.json',
            file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=['json'])
        if path:
            self.controller.save_proposal(path)
            self.app.notify('Propuesta guardada.')

    async def approve_all(self):
        if self.controller.proposal is None:
            raise EditorialError('Todavía no hay propuesta para aprobar.')
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque que estás editando.')
        self.controller.approve_all()
        self._persist_visible_batch_review()
        self.refresh()
        self.app.notify('Todos los bloques han sido aprobados como revisados.')

    async def apply(self):
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque.')
        if self.batch_run is not None and not self.batch_run.complete:
            remaining = self.batch_run.total - self.batch_run.processed
            raise EditorialError(
                f'La secuencia está incompleta: faltan {remaining} subtítulos. '
                'Completa todas las tandas antes de aplicar en Resolve.'
            )
        if self.controller.proposal is None:
            raise EditorialError('No hay una propuesta para aplicar.')
        unreviewed = [d for d in self.controller.proposal.decisions if not d.reviewed]
        if unreviewed:
            confirmed = await self.app.confirm(
                'Aprobar y aplicar',
                f'Hay {len(unreviewed)} bloque{"s" if len(unreviewed) > 1 else ""} pendiente{"s" if len(unreviewed) > 1 else ""} de revisión manual. ¿Deseas aprobar todos los bloques restantes y aplicar la propuesta a Resolve?'
            )
            if not confirmed:
                return
            self.controller.approve_all()
            self.refresh()
        try:
            result = await self.app.run('Aplicando la revisión exacta en Resolve…', self.controller.apply, reraise=True)
            if result:
                self.conflict_cue_indices.clear()
                self.refresh()
                self.app.notify(f'Aplicados {result.item_count} elementos. Comprueba la reproducción en Resolve.')
        except EditorialConflictError as e:
            self.conflict_cue_indices = {c.cue_index: c for c in e.conflicts}
            self.refresh()
            await self._show_conflict_dialog(e)

    async def _show_conflict_dialog(self, error: EditorialConflictError):
        conflict_lines = []
        for c in error.conflicts[:4]:
            conflict_lines.append(
                f"• Pista {c.track_name} (índice {c.track_index}): clip '{c.clip_name}' "
                f"[frames {c.start_frame:g}–{c.end_frame:g}] choca con subtítulo #{c.cue_index + 1} '{c.cue_text}'"
            )
        if len(error.conflicts) > 4:
            conflict_lines.append(f"• … y {len(error.conflicts) - 4} colisión(es) adicionales marcadas en rojo en la tabla.")

        summary_text = (
            f"Se detectaron {len(error.conflicts)} conflicto(s) de clips en las pistas exclusivas de DaVinci Flow.\n\n"
            + "\n".join(conflict_lines)
            + "\n\nLas filas afectadas se resaltaron en rojo en la tabla.\n"
            "Puedes vaciar las pistas de DaVinci Flow ahora mismo o mover los clips ajenos en Resolve."
        )

        async def dismiss(event):
            if hasattr(self.app.page, 'pop_dialog'):
                self.app.page.pop_dialog()
            self.app.page.update()

        async def clean_and_retry(event):
            if hasattr(self.app.page, 'pop_dialog'):
                self.app.page.pop_dialog()
            self.app.page.update()
            await self.clean_tracks(auto_retry=True)

        dialog = ft.AlertDialog(
            modal=True,
            title=text('Conflicto en la línea de tiempo', 18, color='#EF4444', weight=ft.FontWeight.BOLD),
            content=ft.Container(
                ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color='#EF4444', size=24),
                        text('Colisión con clips en pistas de DaVinci Flow', 14, weight=ft.FontWeight.W_600),
                    ], spacing=8),
                    text(summary_text, size=13, selectable=True),
                ], spacing=10, tight=True),
                width=620,
            ),
            alignment=ft.Alignment.CENTER,
            actions=[
                button('Entendido', dismiss),
                button('Limpiar pistas DF y reintentar', clean_and_retry, ft.Icons.CLEANING_SERVICES_OUTLINED, primary=True),
            ],
        )
        if hasattr(self.app.page, 'show_dialog'):
            self.app.page.show_dialog(dialog)
        self.app.page.update()

    async def clean_tracks(self, auto_retry: bool = False):
        if not auto_retry:
            confirmed = await self.app.confirm(
                'Limpiar pistas DaVinci Flow',
                '¿Deseas eliminar todos los clips situados en las pistas DF_CONTEXT, DF_MAIN, DF_ACCENT y DF_SFX de la línea de tiempo activa en Resolve? Las pistas de usuario permanecerán intactas.'
            )
            if not confirmed:
                return
        result = await self.app.run('Limpiando pistas DF en Resolve…', self.controller.clean_df_tracks)
        if result is not None:
            deleted = result.get('deleted_count', 0) if isinstance(result, dict) else 0
            self.conflict_cue_indices.clear()
            self.refresh()
            self.app.notify(f'Pistas DF limpiadas con éxito: {deleted} clips eliminados en Resolve.')
            if auto_retry:
                await self.apply()

    async def undo(self):
        result = await self.app.run('Deshaciendo la muestra de esta secuencia…', self.controller.undo)
        if result:
            self.conflict_cue_indices.clear()
            self.refresh()
            self.app.notify(f'Reversión: {result.status}.')

    async def auto_capture_default(self):
        """Intenta capturar automáticamente los subtítulos generados en Resolve al iniciar."""
        if self.controller.snapshot is not None:
            return
        self.empty.visible = False
        self.initial_loading.visible = True
        self.app.notify('Detectando subtítulos de Resolve…')
        self.app.page.update()
        try:
            track = int(self.track.value)
            first = int(self.first.value)
            last = int(self.last.value)
            result = await asyncio.get_running_loop().run_in_executor(
                self.app.executor,
                lambda: self.controller.read_resolve(track, first, last),
            )
            if result and result.cues:
                self.selected = None
                self.review_card.visible = False
                self.refresh()
                self.app.notify(f'Subtítulos de Resolve detectados ({len(result.cues)} en {result.timeline}).')
        except Exception:
            pass
        finally:
            self.initial_loading.visible = False
            if self.controller.snapshot is None:
                self.empty.visible = True
                self.app.notify('Listo para abrir tu montaje.')
            self.app.page.update()
