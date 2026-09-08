import asyncio
import flet as ft

from davinci_flow.editorial.model import EditorialError
from shared.components import (
    ACCENT, CARD, LINE, MUTED, TEXT, MODES, FORMATS, DENSITIES, button, card, field, scroll_table, select, text,
)


class EditorView:
    def __init__(self, app):
        self.app = app
        self.controller = app.controller
        p = self.controller.preferences
        self.selected = None
        self.track = field('Pista', '1', 72)
        self.fps = field('FPS SRT', '24', 90)
        self.first = field('Desde', '1', 80)
        self.last = field('Hasta', '120', 80)
        self.mode = select('Modo', MODES, p.mode, 190)
        self.format = select('Formato', FORMATS, p.format, 180)
        self.density = select('Densidad', DENSITIES, p.density, 160)
        self.direction = field('Dirección creativa', p.direction, hint_text='Pocas palabras grandes; alternar con planos sin texto.',
                               multiline=True, min_lines=1, max_lines=3)
        self.source_summary = text('Captura los subtítulos de tu montaje o abre un SRT.', color=MUTED)
        self.count = text('Sin fuente', color=MUTED)
        self.table = ft.DataTable(columns=[ft.DataColumn(text(t, color=MUTED)) for t in
            ('Tiempo', 'Contexto', 'Principal', 'Énfasis', 'Plantilla', 'Revisión')],
            rows=[], heading_row_height=38, data_row_min_height=40, data_row_max_height=44,
            column_spacing=18, horizontal_margin=14, show_checkbox_column=False,
            heading_row_color='#242C30', divider_thickness=0.4)
        self.empty = card(ft.Column([ft.Icon(ft.Icons.SUBTITLES_OUTLINED, color=ACCENT, size=32),
            text('Las ideas empiezan con tu montaje', size=17, weight=ft.FontWeight.W_500),
            text('Lee una pista de Resolve o importa un SRT. Después decide qué merece aparecer en pantalla.', color=MUTED)],
            spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=36)
        self.table_view = scroll_table(self.table, width=1120, height=None, expand=True)
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
        self.enabled = ft.Checkbox(label='Mostrar texto', value=True, active_color=ACCENT)
        self.note = field('Nota si reescribes el original', expand=True)
        self.review_card = card(ft.Column([
            ft.Row([text('Revisar composición', 15, weight=ft.FontWeight.W_600), self.enabled],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.original, self.reason, self.visual, *rows,
            self.note,
            ft.Row([button('Guardar revisión', app.bind(self.review), ft.Icons.CHECK, primary=True),
                    button('Siguiente bloque', app.bind(self.next_block), ft.Icons.ARROW_FORWARD)], wrap=True)
        ], spacing=10), visible=False)
        self.content = ft.Column([
            card(ft.Column([
                ft.Row([self.track, self.fps, self.first, self.last,
                    button('Capturar Resolve', app.bind(self.capture), ft.Icons.VIDEO_LIBRARY_OUTLINED),
                    button('Cargar SRT', app.bind(self.open_srt), ft.Icons.UPLOAD_FILE_OUTLINED)], wrap=True, spacing=8, run_spacing=10),
                self.source_summary,
            ], spacing=10)),
            ft.Row([self.mode, self.format, self.density], wrap=True, spacing=10, run_spacing=10),
            self.direction,
            ft.Row([
                ft.Row([
                    button('Proponer con IA', app.bind(self.generate), ft.Icons.AUTO_AWESOME, primary=True),
                    button('Abrir propuesta', app.bind(self.load), ft.Icons.FOLDER_OPEN),
                    button('Guardar', app.bind(self.save), ft.Icons.SAVE_OUTLINED),
                    self.count,
                ], wrap=True, spacing=8, run_spacing=8),
                ft.Row([
                    button('Aplicar revisión', app.bind(self.apply), ft.Icons.PLAY_ARROW_ROUNDED, primary=True,
                           tooltip='Se aplica la revisión guardada, sin volver a llamar a la IA.'),
                    button('Deshacer muestra', app.bind(self.undo), ft.Icons.UNDO_ROUNDED),
                ], wrap=True, spacing=8, run_spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.empty, self.table_view, self.review_card,
        ], spacing=10, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def sync_preferences(self):
        p = self.controller.preferences
        p.mode, p.format, p.density, p.direction = self.mode.value, self.format.value, self.density.value, self.direction.value.strip()

    def refresh(self):
        snapshot, proposal = self.controller.snapshot, self.controller.proposal
        self.table.rows.clear()
        self.empty.visible = snapshot is None
        self.table_view.visible = snapshot is not None
        if snapshot is None:
            return
        self.source_summary.value = f'{snapshot.timeline} · {len(snapshot.cues)} subtítulos · {snapshot.width} × {snapshot.height} · {snapshot.fps:g} fps'
        catalog = {t.id: t.name for t in proposal.templates} if proposal else {}
        for i, cue in enumerate(snapshot.cues):
            decision = proposal.decisions[i] if proposal else None
            values = (f'{cue.start_frame:g}–{cue.end_frame:g}', decision.context if decision else '',
                      (decision.main if decision.enabled else 'Sin rótulo') if decision else cue.text,
                      decision.accent if decision else '',
                      ', '.join(dict.fromkeys(catalog.get(t, '') for t in decision.templates.values())) if decision else 'Por elegir',
                      ('Revisado' if decision.reviewed else 'Pendiente') if decision else 'Fuente')
            cells = [ft.DataCell(ft.Container(content=text(value or '—', color=MUTED if decision and not decision.enabled else TEXT,
                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=value), width=width))
                for value, width in zip(values, (115, 140, 260, 140, 200, 90))]
            self.table.rows.append(ft.DataRow(cells=cells, selected=i == self.selected,
                color='#173A35' if i == self.selected else None, on_select_change=self.app.bind(self.choose, i)))
        reviewed = sum(d.reviewed for d in proposal.decisions) if proposal else 0
        active = sum(d.enabled for d in proposal.decisions) if proposal else 0
        self.count.value = f'{active} rótulos · {reviewed}/{len(snapshot.cues)} revisados' if proposal else f'{len(snapshot.cues)} subtítulos originales'
        self.app.refresh_identity()

    def form_changed(self):
        p = self.controller.proposal
        if p is None or self.selected is None:
            return False
        d = p.decisions[self.selected]
        return (any(f.value.strip() != getattr(d, role).strip() for role, f in self.texts.items())
                or self.enabled.value != d.enabled or self.note.value.strip() != d.edit_note
                or any(self.templates[r].value != tid for r, tid in d.templates.items()))

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
            self.selected = None
            self.review_card.visible = False
            self.refresh()
            self.app.notify('Fuente capturada. Elige la dirección creativa y genera una propuesta.')

    async def open_srt(self):
        if not await self.replacement_allowed():
            return
        path = await self.app.pick_file('Abrir subtítulos', ['srt'])
        if path:
            self.controller.read_srt(path, float(self.fps.value))
            self.selected = None
            self.review_card.visible = False
            self.refresh()

    async def generate(self):
        if not await self.replacement_allowed():
            return
        self.sync_preferences()
        result = await self.app.run('La IA está preparando tu propuesta…', self.controller.generate)
        if result:
            self.selected = None
            self.review_card.visible = False
            self.refresh()
            self.app.notify('Propuesta lista. Revisa cada bloque, incluidos los momentos sin texto.')

    async def choose(self, index):
        if self.controller.proposal is None:
            self.app.notify('Estos son los subtítulos originales. Genera o abre una propuesta para revisarlos.')
            return
        if self.form_changed():
            raise EditorialError('Guarda la revisión del bloque antes de cambiar de fila.')
        self.selected = index
        p = self.controller.proposal
        d = p.decisions[index]
        for role in self.texts:
            self.texts[role].value = getattr(d, role)
            self.templates[role].options = [ft.DropdownOption(key=t.id, text=t.name) for t in p.templates]
            self.templates[role].value = d.templates.get(role)
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
        self.controller.review(self.selected, **texts, templates=assigned,
                               enabled=bool(self.enabled.value), edit_note=self.note.value.strip())
        self.refresh()
        self.app.notify('Revisión del bloque guardada en la propuesta.')

    async def next_block(self):
        if self.selected is not None and self.selected + 1 < len(self.controller.snapshot.cues):
            await self.choose(self.selected + 1)

    async def load(self):
        if not await self.replacement_allowed():
            return
        path = await self.app.pick_file('Abrir propuesta editorial', ['json'])
        if path:
            self.controller.load_proposal(path)
            p = self.controller.preferences
            self.mode.value, self.format.value, self.density.value = p.mode, p.format, p.density
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

    async def apply(self):
        if self.form_changed():
            raise EditorialError('Guarda primero la revisión del bloque.')
        result = await self.app.run('Aplicando la revisión exacta en Resolve…', self.controller.apply)
        if result:
            self.app.notify(f'Aplicados {result.item_count} elementos. Comprueba la reproducción en Resolve.')

    async def undo(self):
        result = await self.app.run('Deshaciendo la muestra de esta secuencia…', self.controller.undo)
        if result:
            self.app.notify(f'Reversión: {result.status}.')

    async def auto_capture_default(self):
        """Intenta capturar automáticamente los subtítulos generados en Resolve al iniciar."""
        if self.controller.snapshot is not None:
            return
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
