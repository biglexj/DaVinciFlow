"""Pestaña dedicada a la corrección rápida, normalización y alineación de subtítulos."""

import asyncio
from pathlib import Path
import re
import flet as ft

from davinci_flow.ai.aligner import (
    ScriptAligner,
    TimelineMarker,
    apply_glossary_to_text,
    parse_glossary_str,
)
from davinci_flow.editorial.model import EditorialError
from davinci_flow.subtitles.model import SubtitleCue
from davinci_flow.subtitles.normalizer import normalize_subtitle_text
from davinci_flow.subtitles.srt_parser import export_cues_to_srt_content
from shared.components import (
    ACCENT, CARD, FIELD, LINE, MUTED, SIDE, TEXT,
    button, card, field, scroll_table, text,
)


class SubtitlesView:
    def __init__(self, app):
        self.app = app
        self.controller = app.controller
        self.cues: list[SubtitleCue] = []
        self.original_cues: list[SubtitleCue] = []
        self.selected_index: int | None = None
        self.markers: tuple[TimelineMarker, ...] = ()
        self.source_id: str | None = None

        # Encabezado e información de fuente
        self.summary_text = text('Captura subtítulos de Resolve o carga un SRT para comenzar.', color=MUTED)
        self.counter_text = text('0 subtítulos', color=MUTED)

        # Controles de Buscar y Reemplazar
        self.find_field = field('Buscar texto', width=200)
        self.replace_field = field('Reemplazar por', width=200)
        self.match_case = ft.Checkbox(label='Mayús/minús', value=False, active_color=ACCENT)

        # Controles de Glosario y Guion IA
        self.glossary_field = field(
            'Glosario rápido',
            hint_text='palabra: Reemplazo, término -> Corrección',
            multiline=True,
            min_lines=1,
            max_lines=2,
            expand=True,
        )
        self.script_field = field(
            'Guion de referencia (opcional para IA)',
            hint_text='Pega aquí el guion para alinear omisiones, ortografía y nombres propios...',
            multiline=True,
            min_lines=1,
            max_lines=3,
        )
        self.detect_markers_check = ft.Checkbox(label='Detectar marcadores clave en línea de tiempo', value=True, active_color=ACCENT)

        # Editor de bloque individual
        self.edit_info = text('', size=12, color=MUTED)
        self.original_label = text('', size=12, color=MUTED, selectable=True)
        self.edit_text_field = field('Texto corregido', multiline=True, min_lines=1, max_lines=3)
        self.edit_text_field.on_submit = app.bind(self.save_and_next)

        self.editor_card = card(
            ft.Column([
                ft.Row([
                    text('Edición de subtítulo', 14, weight=ft.FontWeight.W_600),
                    self.edit_info,
                    ft.IconButton(ft.Icons.CLOSE, tooltip='Cerrar editor', on_click=app.bind(self.close_editor), icon_size=18),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.original_label,
                self.edit_text_field,
                ft.Row([
                    button('Guardar cambio (Enter)', app.bind(self.save_current_cue), ft.Icons.CHECK, primary=True),
                    button('Siguiente subtítulo', app.bind(self.next_cue), ft.Icons.ARROW_FORWARD),
                    button('Restaurar original', app.bind(self.restore_current_cue), ft.Icons.REPLAY_ROUNDED),
                    button('Cerrar', app.bind(self.close_editor), ft.Icons.CLOSE_ROUNDED),
                ], wrap=True, spacing=8),
            ], spacing=8),
            visible=False,
        )

        # Tabla de subtítulos
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(label=text('#', color=MUTED)),
                ft.DataColumn(label=text('Fotogramas / Tiempo', color=MUTED)),
                ft.DataColumn(label=text('Texto Original', color=MUTED)),
                ft.DataColumn(label=text('Texto Corregido', color=MUTED)),
                ft.DataColumn(label=text('Estado', color=MUTED)),
            ],
            rows=[],
            heading_row_height=38,
            data_row_min_height=40,
            data_row_max_height=46,
            column_spacing=16,
            horizontal_margin=14,
            show_checkbox_column=False,
            heading_row_color='#242C30',
            divider_thickness=0.4,
        )
        self.table_view = scroll_table(self.table, width=1180, height=None, expand=True)
        self.table_view.visible = False

        self.empty = card(
            ft.Column([
                ft.Icon(ft.Icons.SPELLCHECK_ROUNDED, color=ACCENT, size=32),
                text('Mesa de corrección de subtítulos', size=17, weight=ft.FontWeight.W_500),
                text('Revisa, normaliza ortografía, busca y reemplaza términos o alinea con guion.', color=MUTED),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=36,
        )

        # Panel colapsable de IA y Guion
        self.ai_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    text('Alineación semántica y corrección con IA (Gemini)', 13, weight=ft.FontWeight.W_600),
                    self.detect_markers_check,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.script_field,
                ft.Row([
                    button('Iniciar corrección con IA', app.bind(self.run_ai_align), ft.Icons.AUTO_AWESOME, primary=True),
                    button('Insertar marcadores en Resolve', app.bind(self.insert_markers), ft.Icons.BOOKMARK_ADDED_ROUNDED),
                ], spacing=8),
            ], spacing=8),
            padding=12,
            bgcolor='#152220',
            border_radius=8,
            border=ft.Border.all(0.8, '#264A43'),
            visible=False,
        )

        # Construcción del layout
        self.content = ft.Column([
            # Fila 1: Resumen y acciones principales
            card(ft.Column([
                ft.Row([
                    self.summary_text,
                    ft.Row([
                        button('Actualizar en Editor', app.bind(self.sync_to_editor), ft.Icons.SYNC_ALT_ROUNDED, primary=True,
                               tooltip='Propaga los subtítulos corregidos hacia la propuesta y mesa editorial'),
                        button('Exportar SRT', app.bind(self.export_srt), ft.Icons.DOWNLOAD_ROUNDED,
                               tooltip='Guarda un archivo .srt con los subtítulos corregidos'),
                        button('Recargar de Resolve', app.bind(self.reload_from_resolve), ft.Icons.REFRESH_ROUNDED,
                               tooltip='Vuelve a leer la pista de subtítulos activa'),
                    ], spacing=8),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),

            # Fila 2: Herramientas rápidas (Buscar y reemplazar, normalización y glosario)
            card(ft.Column([
                ft.Row([
                    text('Herramientas Rápidas de Corrección', 13, weight=ft.FontWeight.W_600),
                    button('Alternar panel IA / Guion', app.bind(self.toggle_ai_panel), ft.Icons.TUNE_ROUNDED),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    self.find_field,
                    self.replace_field,
                    self.match_case,
                    button('Reemplazar todo', app.bind(self.find_and_replace), ft.Icons.FIND_REPLACE_ROUNDED, primary=True),
                    button('Normalizar ortografía', app.bind(self.normalize_all), ft.Icons.AUTO_FIX_HIGH_ROUNDED,
                           tooltip='Aplica mayúsculas, espacios, tildes y signos ¿?, ¡! en español determinista'),
                ], wrap=True, spacing=8, run_spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    self.glossary_field,
                    button('Aplicar glosario', app.bind(self.apply_glossary), ft.Icons.TEXT_FORMAT_ROUNDED),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.ai_container,
            ], spacing=10)),

            # Fila 3: Contador y estado
            ft.Row([
                self.counter_text,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            # Fila 4: Editor de bloque seleccionado
            self.editor_card,

            # Fila 5: Estado vacío o tabla scrolleable
            self.empty,
            self.table_view,
        ], spacing=10, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def load_from_controller(self, force=False):
        snapshot = self.controller.snapshot
        if snapshot is None:
            self.cues = []
            self.original_cues = []
            self.source_id = None
            return

        current_id = f"{snapshot.project_id}_{snapshot.timeline}_{len(snapshot.cues)}"
        if force or self.source_id != current_id or not self.cues:
            self.cues = list(snapshot.cues)
            self.original_cues = list(snapshot.cues)
            self.source_id = current_id
            self.selected_index = None
            self.editor_card.visible = False

    def refresh(self):
        self.load_from_controller()
        snapshot = self.controller.snapshot
        has_subtitles = bool(self.cues)

        self.empty.visible = not has_subtitles
        self.table_view.visible = has_subtitles
        self.table.rows.clear()

        if not has_subtitles:
            self.summary_text.value = 'Captura subtítulos de Resolve o carga un SRT para comenzar.'
            self.counter_text.value = '0 subtítulos'
            return

        cuts_count = len(snapshot.cuts) if snapshot and snapshot.cuts else 0
        cuts_str = f" · {cuts_count} cortes" if cuts_count > 0 else ""
        tl_name = snapshot.timeline if snapshot else "SRT"
        fps = snapshot.fps if snapshot else 24.0
        self.summary_text.value = f'{tl_name} · {len(self.cues)} subtítulos{cuts_str} · {fps:g} fps'

        modified_count = 0
        for i, cue in enumerate(self.cues):
            orig_cue = self.original_cues[i] if i < len(self.original_cues) else cue
            is_mod = cue.text != orig_cue.text
            if is_mod:
                modified_count += 1

            status_chip = ft.Container(
                content=text('Modificado' if is_mod else 'Original', size=11,
                             color='#FFFFFF' if is_mod else MUTED,
                             weight=ft.FontWeight.W_600 if is_mod else ft.FontWeight.NORMAL),
                bgcolor='#2B4A40' if is_mod else '#21262B',
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                border_radius=10,
                border=ft.Border.all(0.6, ACCENT if is_mod else LINE),
            )

            frames_info = f'{cue.start_frame:g}–{cue.end_frame:g} ({cue.duration_frames:g}f)'
            cells = [
                ft.DataCell(ft.Container(content=text(str(i + 1), color=MUTED), width=35)),
                ft.DataCell(ft.Container(content=text(frames_info, color=MUTED, no_wrap=True), width=140)),
                ft.DataCell(ft.Container(content=text(orig_cue.text, color=MUTED, no_wrap=True,
                                                      overflow=ft.TextOverflow.ELLIPSIS, tooltip=orig_cue.text), width=340)),
                ft.DataCell(ft.Container(content=text(cue.text, color=TEXT if is_mod else MUTED, no_wrap=True,
                                                      overflow=ft.TextOverflow.ELLIPSIS, tooltip=cue.text), width=360)),
                ft.DataCell(ft.Container(content=status_chip, width=95)),
            ]
            self.table.rows.append(
                ft.DataRow(
                    cells=cells,
                    selected=i == self.selected_index,
                    color='#173A35' if i == self.selected_index else None,
                    on_select_change=self.app.bind(self.choose_cue, i),
                )
            )

        self.counter_text.value = f'{len(self.cues)} subtítulos en total · {modified_count} corregidos'

    async def choose_cue(self, index: int):
        if not 0 <= index < len(self.cues):
            return
        if self.selected_index == index:
            await self.close_editor()
            return

        self.selected_index = index
        cue = self.cues[index]
        orig_cue = self.original_cues[index] if index < len(self.original_cues) else cue

        self.edit_info.value = f'#{index + 1} | Fotogramas {cue.start_frame:g} a {cue.end_frame:g} ({cue.duration_frames:g}f)'
        self.original_label.value = f'Original: {orig_cue.text}'
        self.edit_text_field.value = cue.text
        self.editor_card.visible = True
        self.refresh()

    async def save_current_cue(self):
        if self.selected_index is None or not 0 <= self.selected_index < len(self.cues):
            return
        new_text = self.edit_text_field.value.strip()
        if not new_text:
            self.app.notify('El texto del subtítulo no puede quedar vacío.')
            return

        current = self.cues[self.selected_index]
        self.cues[self.selected_index] = SubtitleCue(
            text=new_text,
            start_frame=current.start_frame,
            end_frame=current.end_frame,
            track_index=current.track_index,
        )
        self.refresh()
        self.app.notify(f'Subtítulo #{self.selected_index + 1} actualizado.')

    async def save_and_next(self):
        await self.save_current_cue()
        await self.next_cue()

    async def next_cue(self):
        if self.selected_index is not None and self.selected_index + 1 < len(self.cues):
            await self.choose_cue(self.selected_index + 1)

    async def restore_current_cue(self):
        if self.selected_index is None or not 0 <= self.selected_index < len(self.cues):
            return
        orig_cue = self.original_cues[self.selected_index]
        current = self.cues[self.selected_index]
        self.cues[self.selected_index] = SubtitleCue(
            text=orig_cue.text,
            start_frame=current.start_frame,
            end_frame=current.end_frame,
            track_index=current.track_index,
        )
        self.edit_text_field.value = orig_cue.text
        self.refresh()
        self.app.notify(f'Subtítulo #{self.selected_index + 1} restaurado a su texto original.')

    async def close_editor(self):
        self.selected_index = None
        self.editor_card.visible = False
        self.refresh()

    async def toggle_ai_panel(self):
        self.ai_container.visible = not self.ai_container.visible
        self.app.page.update()

    async def find_and_replace(self):
        target = self.find_field.value.strip()
        replacement = self.replace_field.value.strip()
        if not target:
            self.app.notify('Ingresa el término que deseas buscar.')
            return

        pattern = re.compile(re.escape(target) if self.match_case.value else rf"(?i){re.escape(target)}")
        modified_cues = 0
        total_occurrences = 0

        updated_cues = []
        for cue in self.cues:
            new_text, count = pattern.subn(replacement, cue.text)
            if count > 0:
                modified_cues += 1
                total_occurrences += count
                updated_cues.append(
                    SubtitleCue(
                        text=new_text,
                        start_frame=cue.start_frame,
                        end_frame=cue.end_frame,
                        track_index=cue.track_index,
                    )
                )
            else:
                updated_cues.append(cue)

        self.cues = updated_cues
        if self.selected_index is not None:
            self.edit_text_field.value = self.cues[self.selected_index].text
        self.refresh()
        self.app.notify(f'Reemplazo completado: {total_occurrences} sustitución(es) en {modified_cues} subtítulo(s).')

    async def normalize_all(self):
        if not self.cues:
            self.app.notify('No hay subtítulos para normalizar.')
            return

        normalized_count = 0
        updated_cues = []
        for cue in self.cues:
            try:
                norm_text = normalize_subtitle_text(cue.text)
            except Exception:
                norm_text = cue.text

            if norm_text != cue.text:
                normalized_count += 1
            updated_cues.append(
                SubtitleCue(
                    text=norm_text,
                    start_frame=cue.start_frame,
                    end_frame=cue.end_frame,
                    track_index=cue.track_index,
                )
            )

        self.cues = updated_cues
        if self.selected_index is not None:
            self.edit_text_field.value = self.cues[self.selected_index].text
        self.refresh()
        self.app.notify(f'Normalización ortográfica aplicada a {normalized_count} subtítulos.')

    async def apply_glossary(self):
        glossary_raw = self.glossary_field.value.strip()
        if not glossary_raw:
            self.app.notify('Ingresa términos de glosario (ej: término: Reemplazo).')
            return

        glossary = parse_glossary_str(glossary_raw)
        if not glossary:
            self.app.notify('Formato de glosario inválido. Usa: término: Reemplazo')
            return

        changed_count = 0
        updated_cues = []
        for cue in self.cues:
            new_text, changes = apply_glossary_to_text(cue.text, glossary)
            if changes:
                changed_count += 1
            updated_cues.append(
                SubtitleCue(
                    text=new_text,
                    start_frame=cue.start_frame,
                    end_frame=cue.end_frame,
                    track_index=cue.track_index,
                )
            )

        self.cues = updated_cues
        if self.selected_index is not None:
            self.edit_text_field.value = self.cues[self.selected_index].text
        self.refresh()
        self.app.notify(f'Glosario aplicado: {changed_count} subtítulo(s) modificados.')

    async def run_ai_align(self):
        if not self.cues:
            self.app.notify('No hay subtítulos para procesar con IA.')
            return

        script_text = self.script_field.value.strip()
        detect_markers = bool(self.detect_markers_check.value)
        glossary = parse_glossary_str(self.glossary_field.value.strip())
        model_name = self.controller.preferences.model

        def execute():
            aligner = ScriptAligner(model_name=model_name)
            return aligner.align_and_correct(
                cues=self.cues,
                original_script=script_text,
                glossary=glossary,
                detect_markers=detect_markers,
            )

        result = await self.app.run('Alineando y corrigiendo subtítulos con Gemini…', execute)
        if result:
            self.cues = list(result.corrected_cues)
            self.markers = result.markers
            if self.selected_index is not None:
                self.edit_text_field.value = self.cues[self.selected_index].text
            self.refresh()
            markers_info = f' y {len(self.markers)} marcador(es) detectado(s)' if self.markers else ''
            self.app.notify(f'IA: {result.total_corrections} corrección(es){markers_info}.')

    async def sync_to_editor(self):
        if not self.cues:
            self.app.notify('No hay subtítulos para sincronizar.')
            return

        try:
            self.controller.update_cues(self.cues)
            self.app.editor.refresh()
            self.app.notify('✅ Subtítulos corregidos sincronizados exitosamente con la mesa del Editor.')
        except Exception as error:
            self.app.show_error(f'No se pudo sincronizar con el editor: {error}')

    async def export_srt(self):
        if not self.cues:
            self.app.notify('No hay subtítulos para exportar.')
            return

        fps = self.controller.snapshot.fps if self.controller.snapshot else 24.0
        content = export_cues_to_srt_content(self.cues, fps=fps)

        path = await self.app.picker.save_file(
            dialog_title='Exportar subtítulos corregidos (SRT)',
            file_name='subtitulos-corregidos.srt',
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['srt'],
        )
        if path:
            Path(path).write_text(content, encoding='utf-8')
            self.app.notify(f'Subtítulos exportados a {Path(path).name}.')

    async def insert_markers(self):
        if not self.markers:
            self.app.notify('No hay marcadores generados por la IA para insertar.')
            return

        def execute():
            from davinci_flow.application import insert_ai_timeline_markers
            return insert_ai_timeline_markers(self.markers)

        result = await self.app.run('Insertando marcadores en DaVinci Resolve…', execute)
        if result is not None:
            self.app.notify(f'Se insertaron {result} marcadores en la línea de tiempo activa.')

    async def reload_from_resolve(self):
        track = int(self.app.editor.track.value)
        first = int(self.app.editor.first.value)
        last = int(self.app.editor.last.value)

        def execute():
            return self.controller.read_resolve(track, first, last)

        result = await self.app.run('Leyendo subtítulos de Resolve…', execute)
        if result:
            self.load_from_controller(force=True)
            self.refresh()
            self.app.editor.refresh()
            self.app.notify(f'Subtítulos recargados desde Resolve ({len(result.cues)} bloques).')
