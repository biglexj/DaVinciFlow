"""Actualizaciones del producto, mostradas únicamente en Acerca de."""

import inspect
import flet as ft
from shared.components import ACCENT, FIELD, LINE, MUTED, TEXT, button, card, text

GITHUB_RELEASES_URL = 'https://github.com/biglexj/DaVinciFlow/releases'


class UpdatePanel:
    def __init__(self, app):
        self.app = app
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
                    text('Actualizaciones', 15, weight=ft.FontWeight.W_600),
                    text('Canal oficial de GitHub Releases', 11, color=MUTED),
                ], spacing=1, expand=True),
                self.update_status_chip,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(color=LINE, height=14),
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
                on_click=app.bind(self.launch, GITHUB_RELEASES_URL),
                tooltip='Abrir releases en el navegador',
            ),
        ], spacing=12), padding=20)

        self.content = card_updates
        self.refresh()

    def refresh(self):
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
                    text('Pulsa «Buscar actualizaciones» para consultar el canal oficial.', 12, color=MUTED, expand=True),
                ], spacing=6),
                bgcolor='#14181C',
                border=ft.Border.all(1, LINE),
                border_radius=8,
                padding=12,
            )
            return

        error = getattr(self.app, 'update_error', None)
        if error:
            self.update_status_chip.content.value = 'Sin confirmar'
            self.update_status_chip.bgcolor = '#1B262C'
            self.update_status_chip.content.color = MUTED
            self.update_content_box.content = text(error, color=MUTED)
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
                        self.app.bind(self.launch, rel.download_url),
                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                        primary=True,
                    ),
                    button(
                        'Ver en GitHub',
                        self.app.bind(self.launch, rel.release_page_url),
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

    async def launch(self, url):
        result = self.app.page.launch_url(url)
        if inspect.isawaitable(result):
            await result
