"""Un modelo compartido y credenciales ocultas con escaneo dinámico."""

import flet as ft
from davinci_flow.ai.client import FALLBACK_MODELS, list_available_gemini_models
from davinci_flow.ai.credentials import has_gemini_api_key, save_gemini_api_key
from shared.components import ACCENT, MUTED, button, card, field, select, text

MASKED_KEY = '••••••••••••••••'


class SettingsView:
    def __init__(self, app):
        self.app = app
        current_model = app.controller.preferences.model
        has_key = has_gemini_api_key()

        initial_models = list(FALLBACK_MODELS)
        if current_model and current_model not in initial_models:
            initial_models.insert(0, current_model)

        self.model_options = initial_models
        self.model_dropdown = select(
            'Selector de modelos',
            {m: m for m in initial_models},
            value=current_model if current_model in initial_models else (initial_models[0] if initial_models else None),
            width=None,
            expand=True,
        )
        self.model = self.model_dropdown

        self.key = field(
            'Clave API de Gemini',
            value=MASKED_KEY if has_key else '',
            password=True,
            can_reveal_password=False,
        )
        self.key_status = text(
            'Clave configurada y activa.' if has_key
            else 'Configura una clave para generar propuestas y escanear modelos.',
            color=MUTED,
        )
        self.scan_status = text(
            f'Modelos disponibles ({len(initial_models)} predeterminados). Pulsa «Escanear modelos» para consultar la API.',
            color=MUTED,
            size=11,
        )

        scan_btn = button('Escanear modelos', app.bind(self.scan_models), ft.Icons.REFRESH_ROUNDED)

        self.content = ft.Column([
            text('Ajustes del espacio de trabajo', 22, weight=ft.FontWeight.W_600),
            text('El editor usa exactamente el modelo que elijas.', color=MUTED),
            card(ft.Column([
                ft.Row([self.model_dropdown, scan_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.scan_status,
                self.key,
                self.key_status,
                ft.Row([button('Guardar ajustes', app.bind(self.save), ft.Icons.SAVE_OUTLINED, primary=True)], wrap=True),
            ], spacing=16), width=680, padding=22),
            text('Un error de la API conserva tu propuesta anterior y no cambia de modelo. '
                 'Aplicar una revisión guardada no vuelve a llamar a la IA.', color=MUTED),
        ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh(self):
        current_model = self.app.controller.preferences.model
        has_key = has_gemini_api_key()
        if current_model and current_model not in self.model_options:
            self.model_options.insert(0, current_model)
            self.model_dropdown.options = [ft.DropdownOption(key=m, text=m) for m in self.model_options]
        self.model_dropdown.value = current_model
        if has_key:
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'
        else:
            self.key.value = ''
            self.key_status.value = 'Configura una clave para generar propuestas y escanear modelos.'

    async def scan_models(self):
        key_input = self.key.value.strip()
        if key_input and key_input != MASKED_KEY:
            save_gemini_api_key(key_input)
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'

        models = await self.app.run('Escaneando modelos disponibles en Gemini…', list_available_gemini_models)
        if models:
            self.model_options = list(models)
            current_model = self.app.controller.preferences.model
            if current_model and current_model not in self.model_options:
                self.model_options.insert(0, current_model)
            self.model_dropdown.options = [ft.DropdownOption(key=m, text=m) for m in self.model_options]
            if current_model in self.model_options:
                self.model_dropdown.value = current_model
            elif self.model_options:
                self.model_dropdown.value = self.model_options[0]
            self.scan_status.value = f'✅ {len(models)} modelos detectados y disponibles en tu cuenta.'
            self.app.notify(f'Modelos actualizados: {len(models)} disponibles.')
        else:
            self.scan_status.value = 'No se pudieron detectar modelos nuevos. Se conservan los actuales.'
            self.app.notify('No se pudieron escanear modelos. Comprueba tu clave o conexión.')

    async def save(self):
        self.app.editor.sync_preferences()
        self.app.library.save_path()
        selected = self.model_dropdown.value
        if selected:
            self.app.controller.preferences.model = selected.strip()
        self.app.controller.save_preferences()

        key_input = self.key.value.strip()
        if key_input and key_input != MASKED_KEY:
            save_gemini_api_key(key_input)
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'
        elif has_gemini_api_key():
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'

        self.app.refresh_identity()
        self.app.notify('Ajustes guardados. El modelo está compartido con el editor.')
