"""Ajustes del espacio de trabajo con selector IA y panel de actualizaciones."""

import flet as ft
from davinci_flow import __version__
from davinci_flow.ai.client import FALLBACK_MODELS, list_available_gemini_models
from davinci_flow.ai.credentials import has_gemini_api_key, save_gemini_api_key
from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, SIDE, TEXT, button, card, field, select, text

MASKED_KEY = '••••••••••••••••'
GITHUB_RELEASES_URL = 'https://github.com/biglexj/DaVinciFlow/releases'


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

        # Columna Izquierda: IA y Acerca de
        card_ai = card(ft.Column([
            text('Modelo de Inteligencia Artificial', 14, weight=ft.FontWeight.W_600),
            ft.Row([self.model_dropdown, scan_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.scan_status,
            self.key,
            self.key_status,
            ft.Row([button('Guardar ajustes', app.bind(self.save), ft.Icons.SAVE_OUTLINED, primary=True)], wrap=True),
        ], spacing=14), padding=20)

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

        self.col_left = ft.Column([card_ai, card_about, text_disclaimer], spacing=14, expand=1)

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
