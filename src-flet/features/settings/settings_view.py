"""Ajustes del espacio de trabajo con selector IA, voz y panel de actualizaciones."""

from functools import partial
from pathlib import Path

import flet as ft
from davinci_flow import __version__
from davinci_flow.ai.client import (
    FALLBACK_MODELS,
    list_available_gemini_model_info,
)
from davinci_flow.ai.credentials import has_gemini_api_key, has_minimax_api_key, save_gemini_api_key, save_minimax_api_key
from davinci_flow.ai.model_catalog import (
    from_gemini,
    gemini_fallback_capabilities,
    minimax_model_capabilities,
)
from davinci_flow.ai.providers.base import GEMINI_PROVIDER, MINIMAX_MODELS, MINIMAX_PROVIDER, provider_names
from davinci_flow.voice.tts import DEFAULT_SPEECH_MODEL, SPEECH_MODELS, MinimaxSpeechClient, SpeechRequest
from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, SIDE, TEXT, button, card, field, select, text

MASKED_KEY = '••••••••••••••••'
GITHUB_RELEASES_URL = 'https://github.com/biglexj/DaVinciFlow/releases'
VOICE_DIR = Path.home() / '.davinci_flow' / 'voice'
DEFAULT_VOICES = (
    'English_Graceful_Lady',
    'English_Insightful_Speaker',
    'English_Persuasive_Man',
    'Chinese (Mandarin)_Reliable_Executive',
)
PROVIDER_LABELS = {'gemini': 'Google Gemini', 'minimax': 'Minimax'}
KEY_LABELS = {'gemini': 'Clave API de Gemini', 'minimax': 'Clave API de Minimax'}


class SettingsView:
    def __init__(self, app):
        self.app = app
        preferences = app.controller.preferences
        self.provider = str(getattr(preferences, 'provider', GEMINI_PROVIDER) or GEMINI_PROVIDER)
        self.long_context_enabled = bool(getattr(preferences, 'long_context_enabled', False))
        self.capabilities = self._capabilities_for(self.provider)
        self.available_gemini_models = list(FALLBACK_MODELS)
        current_model = preferences.model

        self.provider_dropdown = select(
            'Proveedor de IA',
            {name: PROVIDER_LABELS.get(name, name) for name in provider_names()},
            value=self.provider,
            width=200,
            on_select=app.bind(self.on_provider_change),
        )

        initial_models = list(self._models_for(self.provider, current_model))
        self.model_options = initial_models
        self.model_dropdown = select(
            'Selector de modelos',
            {model: self._model_label(model) for model in initial_models},
            value=current_model if current_model in initial_models else (initial_models[0] if initial_models else None),
            width=None,
            expand=True,
        )
        self.model = self.model_dropdown

        has_key = self._has_key(self.provider)
        self.key = field(
            KEY_LABELS.get(self.provider, 'Clave API'),
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
        self.long_context_toggle = ft.Checkbox(
            label='Mostrar modelos con contexto largo (≥ 100k tokens)',
            value=self.long_context_enabled,
            active_color=ACCENT,
            on_change=app.bind(self.toggle_long_context),
        )

        scan_btn = button('Escanear modelos', app.bind(self.scan_models), ft.Icons.REFRESH_ROUNDED)

        # Columna Izquierda: IA y Acerca de
        card_ai = card(ft.Column([
            text('Modelo de Inteligencia Artificial', 14, weight=ft.FontWeight.W_600),
            ft.Row([self.provider_dropdown], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([self.model_dropdown, scan_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.scan_status,
            self.long_context_toggle,
            self.key,
            self.key_status,
            ft.Row([button('Guardar ajustes', app.bind(self.save), ft.Icons.SAVE_OUTLINED, primary=True)], wrap=True),
        ], spacing=14), padding=20)

        card_voice = self._build_voice_card(app)

        card_about = card(ft.Row([
            ft.Column([
                text('Acerca de DaVinci Flow', 14, weight=ft.FontWeight.W_600),
                text('Información de versión, autoría y canales de apoyo oficial.', 11, color=MUTED),
            ], spacing=2, expand=True),
            button('Ver información', app.bind(app.show_about), ft.Icons.INFO_OUTLINE_ROUNDED),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=16)

        text_disclaimer = text(
            'Un error de la API conserva tu propuesta anterior y no cambia de modelo. '
            'Aplicar una revisión guardada no vuelve a llamar a la IA.',
            color=MUTED,
            size=11,
        )

        self.col_left = ft.Column([card_ai, card_voice, card_about, text_disclaimer], spacing=14, expand=1)

        # Columna Derecha: Panel de Actualizaciones del Sistema
        self.update_status_chip = ft.Container(
            content=text('Al día', 11, weight=ft.FontWeight.W_600, color=ACCENT),
            bgcolor='#153630',
            padding=ft.Padding.symmetric(horizontal=9, vertical=3),
            border_radius=6,
        )

        self.update_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ACCENT, visible=False)
        self.check_button = button(
            'Buscar actualizaciones',
            app.bind(self.manual_check),
            icon=ft.Icons.SYNC_ROUNDED,
            primary=False,
        )

        self.update_content_box = ft.Container(padding=ft.Padding.symmetric(vertical=6))

        card_updates = card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE_ROUNDED, size=22, color=ACCENT),
                ft.Column([
                    text('Actualizaciones de DaVinci Flow', 15, weight=ft.FontWeight.W_600),
                    text('Canal oficial de GitHub Releases', 11, color=MUTED),
                ], spacing=1),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(color=LINE, height=14),
            ft.Row([
                text('Versión instalada:', 12, color=MUTED),
                ft.Container(
                    content=text(f'v{__version__}', 12, weight=ft.FontWeight.W_600, color=TEXT),
                    bgcolor=FIELD,
                    border=ft.Border.all(1, LINE),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                    border_radius=6,
                ),
                ft.Container(expand=True),
                self.update_status_chip,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                self.check_button,
                self.update_spinner,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.update_content_box,
            ft.Divider(color=LINE, height=14),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.HISTORY_ROUNDED, size=16, color=MUTED),
                    text('Ver historial completo de versiones en GitHub ↗', 11, color=MUTED),
                ], spacing=6),
                ink=True,
                padding=ft.Padding.symmetric(vertical=4, horizontal=6),
                border_radius=6,
                on_click=lambda _: self.app.page.launch_url(GITHUB_RELEASES_URL),
                tooltip='Abrir releases en el navegador',
            ),
        ], spacing=12), padding=20)

        self.updater_card = card_updates
        self.col_right = ft.Column([card_updates], spacing=14, expand=1)

        # Layout responsivo a 2 columnas simétricas
        two_columns = ft.Row(
            [self.col_left, self.col_right],
            spacing=20,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self.content = ft.Column([
            text('Ajustes del espacio de trabajo', 22, weight=ft.FontWeight.W_600),
            text('Configura la inteligencia editorial y verifica las actualizaciones oficiales.', color=MUTED),
            two_columns,
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

        self.refresh_updates_ui()

    def _capabilities_for(self, provider):
        if provider == MINIMAX_PROVIDER:
            return list(minimax_model_capabilities(MINIMAX_MODELS))
        return list(gemini_fallback_capabilities())

    def _models_for(self, provider, current_model=''):
        """Lista los modelos disponibles y conserva cualquier selección actual."""
        if provider == MINIMAX_PROVIDER:
            base_models = list(MINIMAX_MODELS)
        else:
            base_models = list(self.available_gemini_models or FALLBACK_MODELS)
        if self.long_context_enabled:
            eligible = {cap.model_id for cap in self.capabilities
                        if cap.long_context and cap.supports_structured_output}
            models = [model for model in base_models if model in eligible]
        else:
            models = base_models
        if not self.long_context_enabled and current_model and current_model not in models:
            models.insert(0, current_model)
        return models

    def _model_label(self, model):
        by_id = {cap.model_id: cap for cap in self.capabilities}
        capability = by_id.get(model)
        if capability and capability.input_token_limit:
            return f'{model} · {capability.context_label}'
        if self.long_context_enabled:
            return f'{model} · capacidad no verificada'
        return model

    def _model_dropdown_options(self, models):
        labels = {model: self._model_label(model) for model in models}
        return [ft.DropdownOption(key=model, text=label) for model, label in labels.items()]

    async def toggle_long_context(self, event):
        self.long_context_enabled = bool(self.long_context_toggle.value)
        current = self.model_dropdown.value or self.app.controller.preferences.model
        self.model_options = self._models_for(self.provider, current)
        self.model_dropdown.options = self._model_dropdown_options(self.model_options)
        self.model_dropdown.value = current if current in self.model_options else (
            self.model_options[0] if self.model_options else None
        )
        long_count = sum(cap.long_context and cap.supports_structured_output for cap in self.capabilities)
        if self.long_context_enabled and not long_count:
            self.scan_status.value = 'Escanea los modelos disponibles para comprobar cuáles admiten contexto largo.'
        elif self.long_context_enabled and self.provider == MINIMAX_PROVIDER:
            self.scan_status.value = f'{long_count} modelo(s) Minimax con contexto largo identificados.'
        self.app.page.update()

    def _has_key(self, provider):
        """Indica si el proveedor seleccionado tiene credencial disponible."""
        return has_minimax_api_key() if provider == MINIMAX_PROVIDER else has_gemini_api_key()

    def _build_voice_card(self, app):
        """Construye la tarjeta de locución con Minimax."""
        self.voice_text = field(
            'Texto de la locución',
            value='',
            multiline=True,
            min_lines=2,
            max_lines=5,
        )
        self.voice_select = select(
            'Voz',
            {voice: voice for voice in DEFAULT_VOICES},
            value=DEFAULT_VOICES[0],
            width=None,
            expand=True,
        )
        self.voice_model = select(
            'Modelo de voz',
            {model: model for model in SPEECH_MODELS},
            value=DEFAULT_SPEECH_MODEL,
            width=190,
        )
        self.voice_speed = ft.Slider(
            min=0.5,
            max=2.0,
            divisions=15,
            value=1.0,
            label='Velocidad',
            active_color=ACCENT,
        )
        self.voice_status = text(
            'La locución se guarda en disco y sus subtítulos alineados quedan disponibles para la pista nativa.',
            color=MUTED,
            size=11,
        )
        self.voice_button = button(
            'Generar locución',
            app.bind(self.synthesize_voice),
            ft.Icons.RECORD_VOICE_OVER_ROUNDED,
            primary=True,
        )
        return card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED, size=22, color=ACCENT),
                ft.Column([
                    text('Locución con Minimax', 14, weight=ft.FontWeight.W_600),
                    text('Sintetiza narración con voz y obtén los subtítulos alineados.', 11, color=MUTED),
                ], spacing=1),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.voice_text,
            ft.Row([self.voice_select, self.voice_model], spacing=10, wrap=True),
            self.voice_speed,
            ft.Row([self.voice_button], wrap=True),
            self.voice_status,
        ], spacing=12), padding=20)

    async def on_provider_change(self, event):
        """Cambia el proveedor activo y actualiza modelos, clave y avisos."""
        provider = self.provider_dropdown.value or GEMINI_PROVIDER
        self.provider = provider
        self.capabilities = self._capabilities_for(provider)
        if provider == GEMINI_PROVIDER:
            self.available_gemini_models = list(FALLBACK_MODELS)
        models = self._models_for(provider)
        self.model_options = models
        self.model_dropdown.options = self._model_dropdown_options(models)
        self.model_dropdown.value = models[0] if models else None
        self.key.label = KEY_LABELS.get(provider, 'Clave API')
        has_key = self._has_key(provider)
        self.key.value = MASKED_KEY if has_key else ''
        self.key_status.value = (
            'Clave configurada y activa.' if has_key
            else 'Configura una clave para generar propuestas.'
        )
        self.scan_status.value = (
            f'Modelos disponibles ({len(models)}). Minimax publica su catálogo por su API; '
            'no requiere escaneo.' if provider == MINIMAX_PROVIDER
            else f'Modelos disponibles ({len(models)} predeterminados). Pulsa «Escanear modelos» para consultar la API.'
        )
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
        self.long_context_enabled = bool(getattr(self.app.controller.preferences, 'long_context_enabled', False))
        self.long_context_toggle.value = self.long_context_enabled
        self.provider_dropdown.value = self.provider
        self.capabilities = self._capabilities_for(self.provider)
        self.model_options = self._models_for(self.provider, current_model)
        self.model_dropdown.options = self._model_dropdown_options(self.model_options)
        self.model_dropdown.value = current_model if current_model in self.model_options else (
            self.model_options[0] if self.model_options else None
        )
        has_key = self._has_key(self.provider)
        self.key.label = KEY_LABELS.get(self.provider, 'Clave API')
        if has_key:
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'
        else:
            self.key.value = ''
            self.key_status.value = 'Configura una clave para generar propuestas y escanear modelos.'
        self.refresh_updates_ui()

    def refresh_updates_ui(self):
        """Actualiza el estado visual del panel de actualizaciones según el estado de la app."""
        rel = getattr(self.app, 'latest_release', None)
        checking = getattr(self.app, 'checking_updates', False)

        self.update_spinner.visible = checking
        self.check_button.disabled = checking

        has_checked = getattr(self.app, 'has_checked_updates', False)

        if checking:
            self.update_status_chip.content.value = 'Buscando…'
            self.update_status_chip.bgcolor = '#1B262C'
            self.update_status_chip.content.color = MUTED
            self.update_content_box.content = ft.Row([
                text('Consultando GitHub Releases en segundo plano…', 12, color=MUTED),
            ], spacing=8)
            return

        if not has_checked and not rel:
            self.update_status_chip.content.value = 'Comprobación pendiente'
            self.update_status_chip.bgcolor = '#1B262C'
            self.update_status_chip.content.color = MUTED
            self.update_content_box.content = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=MUTED, size=16),
                    text('Pulsa «Buscar actualizaciones» para consultar el canal oficial.', 12, color=MUTED),
                ], spacing=6),
                bgcolor='#14181C',
                border=ft.Border.all(1, LINE),
                border_radius=8,
                padding=12,
            )
            return

        if rel and rel.is_newer:
            self.update_status_chip.content.value = f'Nueva v{rel.version}'
            self.update_status_chip.bgcolor = '#382B14'
            self.update_status_chip.content.color = '#FFA726'

            notes_scroll = ft.Container(
                content=ft.Column(
                    [text(rel.sanitized_notes, size=11, color=TEXT, selectable=True)],
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
                height=130,
                bgcolor=FIELD,
                border=ft.Border.all(1, LINE),
                border_radius=8,
                padding=10,
            )

            self.update_content_box.content = ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color='#00E5FF', size=18),
                    text(f'¡Nueva versión v{rel.version} disponible!', 13, weight=ft.FontWeight.BOLD, color=TEXT),
                ], spacing=6),
                text(
                    f"Publicada: {rel.published_at[:10] if rel.published_at else 'Reciente'}",
                    11,
                    color=MUTED,
                ),
                ft.Container(height=2),
                text('Novedades destacadas:', 11, weight=ft.FontWeight.W_600, color=ACCENT),
                notes_scroll,
                ft.Container(height=2),
                ft.Row([
                    button(
                        'Descargar actualización',
                        lambda _: self.app.page.launch_url(rel.download_url),
                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                        primary=True,
                    ),
                    button(
                        'Ver en GitHub',
                        lambda _: self.app.page.launch_url(rel.release_page_url),
                        icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                    ),
                ], spacing=8, wrap=True),
            ], spacing=6)
        else:
            self.update_status_chip.content.value = 'Al día'
            self.update_status_chip.bgcolor = '#153630'
            self.update_status_chip.content.color = ACCENT

            self.update_content_box.content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=ACCENT, size=17),
                        text('Tu versión está completamente al día.', 12, weight=ft.FontWeight.W_600, color=TEXT),
                    ], spacing=6),
                    text(
                        'DaVinci Flow cuenta con las plantillas, motores de subtítulos y optimizaciones más recientes.',
                        11,
                        color=MUTED,
                    ),
                ], spacing=4),
                bgcolor='#14211D',
                border=ft.Border.all(1, '#1E3E36'),
                border_radius=8,
                padding=12,
            )

    async def manual_check(self):
        await self.app.check_updates(manual=True)

    async def scan_models(self):
        if self.provider == MINIMAX_PROVIDER:
            self.scan_status.value = 'Minimax publica su catálogo por su API; no requiere escaneo.'
            self.app.notify('El escaneo de modelos solo aplica a Google Gemini.')
            return

        key_input = self.key.value.strip()
        if key_input and key_input != MASKED_KEY:
            save_gemini_api_key(key_input)
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'

        model_info = await self.app.run('Escaneando modelos y límites disponibles en Gemini…', list_available_gemini_model_info)
        if model_info:
            self.capabilities = [from_gemini(info) for info in model_info]
            self.available_gemini_models = [info.model_id for info in model_info]
            current_model = self.app.controller.preferences.model
            self.model_options = self._models_for(self.provider, current_model)
            self.model_dropdown.options = self._model_dropdown_options(self.model_options)
            self.model_dropdown.value = current_model if current_model in self.model_options else (
                self.model_options[0] if self.model_options else None)
            long_count = sum(cap.long_context and cap.supports_structured_output for cap in self.capabilities)
            self.scan_status.value = f'✅ {len(model_info)} modelos disponibles; {long_count} con contexto largo.'
            self.app.notify(f'Modelos actualizados: {len(model_info)} disponibles.')
        else:
            self.scan_status.value = 'No se pudieron detectar modelos nuevos. Se conservan los actuales.'
            self.app.notify('No se pudieron escanear modelos. Comprueba tu clave o conexión.')

    async def synthesize_voice(self):
        """Genera la locución con Minimax y deja el archivo listo para Resolve."""
        narration = self.voice_text.value.strip()
        if not narration:
            self.voice_status.value = 'Escribe el texto que quieres locutar.'
            self.app.notify('El texto de la locución está vacío.')
            return

        request = SpeechRequest(
            text=narration,
            voice_id=self.voice_select.value or DEFAULT_VOICES[0],
            model=self.voice_model.value or DEFAULT_SPEECH_MODEL,
            speed=float(self.voice_speed.value or 1.0),
            language_boost='Spanish',
        )
        target = VOICE_DIR / 'locucion.wav'
        operation = partial(self._run_voice, request, target)
        result = await self.app.run('Sintetizando la locución con Minimax…', operation)
        if not result:
            return
        path, duration_ms, cue_count = result
        self.voice_status.value = (
            f'✅ Locución guardada en {path} ({duration_ms / 1000:.1f} s, {cue_count} subtítulos alineados).'
        )
        self.app.notify('Locución generada.')

    @staticmethod
    def _run_voice(request, target):
        """Sintetiza la locución y guarda el archivo; devuelve el resumen."""
        client = MinimaxSpeechClient()
        result, path = client.synthesize_to_file(request, target)
        return str(path), result.duration_ms, len(result.cues)

    async def save(self):
        self.app.editor.sync_preferences()
        self.app.library.save_path()
        selected = self.model_dropdown.value
        if self.long_context_enabled and selected not in self.model_options:
            self.app.notify('Escanea los modelos o elige uno que admita contexto largo antes de guardar.')
            return
        if selected:
            self.app.controller.preferences.model = selected.strip()
        provider = self.provider_dropdown.value or GEMINI_PROVIDER
        self.app.controller.preferences.provider = provider
        self.app.controller.preferences.long_context_enabled = bool(self.long_context_toggle.value)
        self.app.controller.save_preferences()

        key_input = self.key.value.strip()
        if key_input and key_input != MASKED_KEY:
            if provider == MINIMAX_PROVIDER:
                save_minimax_api_key(key_input)
            else:
                save_gemini_api_key(key_input)
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'
        elif self._has_key(provider):
            self.key.value = MASKED_KEY
            self.key_status.value = 'Clave configurada y activa.'

        self.app.refresh_identity()
        self.app.notify(f'Ajustes guardados. Proveedor activo: {PROVIDER_LABELS.get(provider, provider)}.')
