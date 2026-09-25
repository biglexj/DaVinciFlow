"""Vista del Asistente Creativo de DaVinci Flow para conceptualización y assets."""

import flet as ft

from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, TEXT, button, card, field, text


class AssistantView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.messages_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self.prompt_field = field(
            "Mensaje al Asistente",
            hint_text="Pregunta sobre ideas, tono narrativo, B-Rolls o dirección creativa…",
            expand=True,
            multiline=False,
            on_submit=self.app.bind(self.send_message),
        )
        self.context_summary = text("Sin secuencia capturada.", color=MUTED, size=12)

        # Sugerencias rápidas de brainstorming
        quick_prompts = [
            ("💡 Ritmo visual", "Sugiere cómo dosificar el ritmo de subtítulos y pausas para mantener máxima atención."),
            ("🎬 Selección B-Roll", "¿Qué momentos del guion justifican mejor insertar clips de B-Roll o imágenes?"),
            ("🔊 Sonido sutil", "¿Qué efectos de sonido (pop, whoosh) recomiendas para acentuar ideas clave sin saturar?"),
            ("✨ Dirección para Shorts", "Genera una dirección creativa de alto impacto para formato vertical de 60s."),
        ]
        chips = [
            ft.Container(
                content=text(label, size=11, weight=ft.FontWeight.W_500, color=TEXT),
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                border_radius=16,
                bgcolor="#1C2428",
                border=ft.Border.all(0.8, LINE),
                ink=True,
                on_click=self.app.bind(self.use_suggestion, prompt),
            )
            for label, prompt in quick_prompts
        ]

        self.content = ft.Column([
            text("Asistente IA de Edición", 22, weight=ft.FontWeight.W_600),
            text("Brainstorming narrativo, conceptos visuales y sugerencias de assets antes de montar.", color=MUTED),
            card(ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, color=ACCENT, size=18),
                self.context_summary,
            ], spacing=8), padding=10),
            ft.Row(chips, wrap=True, spacing=6, run_spacing=6),
            card(self.messages_column, padding=12, expand=True),
            ft.Row([
                self.prompt_field,
                button("Enviar", self.app.bind(self.send_message), ft.Icons.SEND_ROUNDED, primary=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self._add_system_greeting()

    def _add_system_greeting(self):
        greeting = (
            "¡Hola, creador! Soy tu Asistente IA de DaVinci Flow. Puedo ayudarte a pulir "
            "tu dirección narrativa, recomendarte qué tipo de B-Rolls o efectos sonoros "
            "asociar a tus frases clave, y generar una 'Dirección creativa' lista para transferir a la mesa de edición."
        )
        self._append_message("Asistente", greeting, is_ai=True)

    def _append_message(self, sender: str, content: str, is_ai: bool = False, can_transfer: bool = False):
        bg = "#172A24" if is_ai else "#1B2226"
        border_c = ACCENT if is_ai else LINE
        sender_color = ACCENT if is_ai else MUTED

        actions = []
        if can_transfer:
            actions.append(
                button(
                    "📌 Aplicar como Dirección Creativa",
                    self.app.bind(self.transfer_to_editor, content),
                    ft.Icons.NORTH_EAST_ROUNDED,
                    tooltip="Copia esta propuesta directamente al campo 'Dirección creativa' del Editor",
                )
            )

        msg_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME if is_ai else ft.Icons.PERSON, size=14, color=sender_color),
                    text(sender, size=12, weight=ft.FontWeight.W_600, color=sender_color),
                ], spacing=6),
                text(content, size=13, selectable=True),
                *([ft.Row(actions, alignment=ft.MainAxisAlignment.END)] if actions else []),
            ], spacing=6),
            padding=12,
            border_radius=10,
            bgcolor=bg,
            border=ft.Border.all(0.8, border_c),
        )
        self.messages_column.controls.append(msg_card)

    async def use_suggestion(self, prompt: str):
        self.prompt_field.value = prompt
        self.app.page.update()
        await self.send_message()

    async def transfer_to_editor(self, content: str):
        # Limpia preámbulos y extrae directriz concisa
        direction_text = content.strip().split("\n\n")[0].replace('"', '')
        if len(direction_text) > 160:
            direction_text = direction_text[:157] + "…"
        self.app.editor.direction.value = direction_text
        self.controller.preferences.direction = direction_text
        self.controller.save_preferences()
        self.app.notify("¡Dirección transferida al Editor!")
        await self.app.navigate("editor")

    async def send_message(self):
        query = self.prompt_field.value.strip()
        if not query:
            return
        self.prompt_field.value = ""
        self._append_message("Tú", query, is_ai=False)
        self.app.page.update()

        # Generar respuesta contextual
        snapshot = self.controller.snapshot
        context_str = ""
        if snapshot:
            context_str = (
                f"Secuencia activa: {snapshot.timeline} · {len(snapshot.cues)} subtítulos · "
                f"{snapshot.width}x{snapshot.height} · {snapshot.fps:g} fps"
            )

        prompt_with_context = (
            f"Contexto del proyecto: {context_str or 'Sin captura directa'}\n\n"
            f"Consulta del creador: {query}\n\n"
            f"Responde de forma concisa, práctica y cinematográfica (máximo 3 párrafos). "
            f"Incluye una frase sintetizada final recomendada como 'Dirección creativa'."
        )

        try:
            generator = self.controller.text_generator()
            response = await self.app.run("Consultando al Asistente IA…", lambda: generator.generate(prompt_with_context))
            self._append_message("Asistente", response, is_ai=True, can_transfer=True)
        except Exception as err:
            self._append_message("Asistente", f"No pude completar la consulta: {err}", is_ai=True)
        self.app.page.update()

    def refresh(self):
        snapshot = self.controller.snapshot
        if snapshot:
            self.context_summary.value = (
                f"Secuencia activa: {snapshot.timeline} · {len(snapshot.cues)} subtítulos · "
                f"{snapshot.width} × {snapshot.height} · {snapshot.fps:g} fps"
            )
        else:
            self.context_summary.value = "Sin secuencia capturada. Captura primero en el Editor."
