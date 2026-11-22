"""Cuenta de Aurora y ajustes del proveedor y modelo editorial."""


import flet as ft
from davinci_flow.ai.client import list_available_gemini_model_info
from davinci_flow.ai.credentials import has_gemini_api_key, has_minimax_api_key, save_gemini_api_key, save_minimax_api_key
from davinci_flow.ai.model_catalog import (
    from_gemini,
    minimax_model_capabilities,
)
from davinci_flow.ai.providers.base import GEMINI_PROVIDER, MINIMAX_MODELS, MINIMAX_PROVIDER, provider_names
from shared.components import MUTED, button, card, field, select, text

MASKED_KEY = '••••••••••••••••'
PROVIDER_LABELS = {'gemini': 'Google Gemini', 'minimax': 'Minimax'}
KEY_LABELS = {'gemini': 'Clave API de Gemini', 'minimax': 'Clave API de Minimax'}
KEY_PROMPTS = {'gemini': 'Ingresa tu clave API de Gemini.', 'minimax': 'Ingresa tu clave API de Minimax.'}


class SettingsView:
    def __init__(self, app):
        self.app = app
        preferences = app.controller.preferences
        self.provider = str(getattr(preferences, 'provider', GEMINI_PROVIDER) or GEMINI_PROVIDER)
        self.gemini_models = ()

        self.provider_dropdown = select(
            'Proveedor de IA',
            {name: PROVIDER_LABELS.get(name, name) for name in provider_names()},
            value=self.provider,
            width=200,
            on_select=app.bind(self.on_provider_change),
        )

        self.model_dropdown = select('Selector de modelos', {}, width=None, expand=True)
        self.model = self.model_dropdown

        self.key = field('Clave API', password=True, can_reveal_password=False)
        self.key_status = text('', color=MUTED)
        self.scan_status = text('', color=MUTED, size=11)
        self._refresh_provider_controls(preferences.model)
        scan_btn = button('Escanear modelos', app.bind(self.scan_models), ft.Icons.REFRESH_ROUNDED)

        # Ajustes del modelo editorial.
        card_ai = card(ft.Column([
            text('Modelo de Inteligencia Artificial', 14, weight=ft.FontWeight.W_600),
            ft.Row([self.provider_dropdown], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([self.model_dropdown, scan_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.scan_status,
            self.key,
            self.key_status,
            ft.Row([button('Guardar ajustes', app.bind(self.save), ft.Icons.SAVE_OUTLINED, primary=True)], wrap=True),
        ], spacing=14), padding=20)

        self.account_card = app.voice.account_card
        card_ai.col = {'xs': 12, 'lg': 6}
        self.account_card.col = {'xs': 12, 'lg': 6}
        self.content = ft.Column([
            ft.ResponsiveRow([self.account_card, card_ai], spacing=18, run_spacing=14,
                             breakpoints={'xs': 0, 'lg': 900}),
            text('Un error de la API conserva tu propuesta anterior y no cambia de modelo. '
                 'Aplicar una revisión guardada no vuelve a llamar a la IA.', color=MUTED, size=11),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True,
           horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    async def open(self):
        await self.app.voice.open()
        self.app.voice.render_account()

    def _capabilities_for(self, provider):
        if provider == MINIMAX_PROVIDER:
            return list(minimax_model_capabilities(MINIMAX_MODELS))
        return [from_gemini(info) for info in self.gemini_models]

    def _update_model_dropdown(self, current_model, has_key):
        if not has_key:
            models = []
        elif self.provider == MINIMAX_PROVIDER:
            models = list(MINIMAX_MODELS)
            if current_model and current_model not in models:
                models.insert(0, current_model)
            current_model = current_model or models[0]
        else:
            models = [info.model_id for info in self.gemini_models]
        self.model_dropdown.options = [ft.DropdownOption(key=model, text=model) for model in models]
        self.model_dropdown.value = current_model if current_model in models else None
        self.model_dropdown.disabled = not models
        self.model_dropdown.hint_text = f'Modelo guardado: {current_model}' if has_key and current_model else None

    def _has_key(self, provider):
        """Indica si el proveedor seleccionado tiene credencial disponible."""
        return has_minimax_api_key() if provider == MINIMAX_PROVIDER else has_gemini_api_key()

    def _refresh_provider_controls(self, current_model=''):
        has_key = self._has_key(self.provider)
        if not has_key and self.provider == GEMINI_PROVIDER:
            self.gemini_models = ()
        self.capabilities = self._capabilities_for(self.provider)
        self._update_model_dropdown(current_model, has_key)
        self.key.label = KEY_LABELS[self.provider]
        self.key.value = MASKED_KEY if has_key else ''
        self.key_status.value = 'Clave configurada.' if has_key else KEY_PROMPTS[self.provider]
        self.scan_status.visible = has_key
        if self.provider == MINIMAX_PROVIDER:
            self.scan_status.value = 'Modelos de Minimax preconfigurados.'
        elif self.gemini_models:
            self.scan_status.value = f'{len(self.gemini_models)} modelos disponibles.'
        else:
            self.scan_status.value = 'Escanea modelos para consultar el catálogo de Gemini.'

    def _save_key(self):
        key_input = self.key.value.strip()
        if not key_input or key_input == MASKED_KEY:
            return
        if self.provider == MINIMAX_PROVIDER:
            save_minimax_api_key(key_input)
        else:
            save_gemini_api_key(key_input)
            self.gemini_models = ()
        current_model = self.model_dropdown.value or ''
        self._refresh_provider_controls(current_model)

    async def on_provider_change(self, event):
        """Cambia el proveedor activo y actualiza modelos, clave y avisos."""
        self.provider = self.provider_dropdown.value or GEMINI_PROVIDER
        preferences = self.app.controller.preferences
        self._refresh_provider_controls(preferences.model if preferences.provider == self.provider else '')
        self.page_update()

    def page_update(self):
        """Actualiza la vista tras un cambio de proveedor."""
        try:
            self.app.page.update()
        except Exception:
            pass

    def refresh(self):
        current_model = self.app.controller.preferences.model
        self.provider = str(getattr(self.app.controller.preferences, 'provider', GEMINI_PROVIDER) or GEMINI_PROVIDER)
        self.provider_dropdown.value = self.provider
        self._refresh_provider_controls(current_model)

    async def scan_models(self):
        key_input = self.key.value.strip()
        if (not key_input or key_input == MASKED_KEY) and not self._has_key(self.provider):
            self._refresh_provider_controls()
            self.app.notify(KEY_PROMPTS[self.provider])
            return
        if self.provider == MINIMAX_PROVIDER:
            self.app.notify('El escaneo de modelos solo aplica a Google Gemini.')
            return

        current_model = self.model_dropdown.value
        preferences = self.app.controller.preferences
        if not current_model and preferences.provider == self.provider:
            current_model = preferences.model
        self._save_key()

        model_info = await self.app.run(
            'Escaneando modelos de Gemini…', lambda: list_available_gemini_model_info(use_fallback=False),
        )
        if model_info:
            self.gemini_models = model_info
            self._refresh_provider_controls(current_model)
            self.app.notify(f'Modelos actualizados: {len(model_info)} disponibles.')
        else:
            self.scan_status.visible = True
            self.scan_status.value = 'No se pudo confirmar el catálogo de Gemini.'
            self.app.notify('No se pudieron escanear modelos. Comprueba tu clave o conexión.')

    async def save(self):
        self.app.editor.sync_preferences()
        self._save_key()
        preferences = self.app.controller.preferences
        selected = self.model_dropdown.value
        if selected:
            preferences.model = selected.strip()
            preferences.provider = self.provider
        self.app.controller.save_preferences()
        self.app.refresh_identity()
        if self.provider != preferences.provider:
            self.app.notify('Elige un modelo para activar este proveedor.' if self._has_key(self.provider)
                            else KEY_PROMPTS[self.provider])
        else:
            self.app.notify(f'Ajustes guardados. Proveedor activo: {PROVIDER_LABELS[preferences.provider]}.')
