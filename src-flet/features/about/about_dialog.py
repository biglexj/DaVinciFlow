"""Diálogo modal e información oficial de «Acerca de DaVinci Flow»."""

import platform
import flet as ft
from davinci_flow import __version__
from shared.components import ACCENT, LINE, MUTED, SIDE, TEXT, button, text

DONATIONS_URL = 'https://www.biglexj.com/donaciones'
BUY_ME_A_COFFEE_URL = 'https://buymeacoffee.com/biglexj'
FEEDBACK_URL = 'https://github.com/biglexj/DaVinciFlow/issues'
GITHUB_URL = 'https://github.com/biglexj'


def build_about_dialog(app) -> ft.AlertDialog:
    """Construye el diálogo modal Acerca de DaVinci Flow con los estándares del ecosistema."""
    branding = getattr(app, 'branding_path', None)
    icon_src = str(branding / 'icon-transparent.png') if branding else None

    async def dismiss(event=None):
        if hasattr(app.page, 'pop_dialog'):
            app.page.pop_dialog()
        app.page.update()

    def launch(url):
        def handler(event=None):
            if hasattr(app.page, 'launch_url'):
                app.page.launch_url(url)
        return handler

    header_items = []
    if icon_src:
        header_items.append(ft.Image(src=icon_src, width=44, height=44))

    header_items.append(
        ft.Column([
            text('DaVinci Flow', 20, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Container(
                content=text(f'v{__version__} • Licencia MIT', 11, weight=ft.FontWeight.W_600, color=ACCENT),
                bgcolor='#153630',
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                border_radius=6,
            ),
        ], spacing=2)
    )

    content = ft.Container(
        width=460,
        content=ft.Column([
            ft.Row(header_items, alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            ft.Container(height=4),
            text('Desarrollado por biglexj (2026)', 13, weight=ft.FontWeight.W_600,
                 text_align=ft.TextAlign.CENTER, color=TEXT),
            text(
                'Automatización modular de subtítulos, Fusion y edición para DaVinci Resolve.',
                12, color=MUTED, text_align=ft.TextAlign.CENTER
            ),
            text(
                'Si esta herramienta agiliza tu flujo de trabajo diario, considera apoyar su desarrollo continuo.',
                11, color='#8E9A9F', text_align=ft.TextAlign.CENTER
            ),
            text(
                f'{platform.python_implementation()} · Flet v{ft.__version__}',
                10, color=MUTED, text_align=ft.TextAlign.CENTER
            ),
            ft.Divider(color=LINE, height=18),
            ft.Column([
                button(
                    'Donaciones Oficiales (Yape / Plin / Web)',
                    launch(DONATIONS_URL),
                    icon=ft.Icons.VOLUNTEER_ACTIVISM_OUTLINED,
                    primary=True,
                    width=430,
                ),
                button(
                    'Buy Me a Coffee ☕',
                    launch(BUY_ME_A_COFFEE_URL),
                    icon=ft.Icons.COFFEE_ROUNDED,
                    width=430,
                ),
                button(
                    'Enviar Feedback / Reportar Error 💬',
                    launch(FEEDBACK_URL),
                    icon=ft.Icons.FEEDBACK_OUTLINED,
                    width=430,
                ),
                button(
                    'Perfil de GitHub',
                    launch(GITHUB_URL),
                    icon=ft.Icons.CODE_ROUNDED,
                    width=430,
                ),
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=6),
        padding=ft.Padding.symmetric(vertical=4, horizontal=4),
    )

    def close_dialog():
        dialog.open = False
        try:
            dialog.update()
        except Exception:
            pass
        if hasattr(app.page, 'pop_dialog'):
            try:
                app.page.pop_dialog()
            except Exception:
                pass
        try:
            app.page.update()
        except Exception:
            pass

    async def dismiss(event=None):
        close_dialog()

    async def check_updates(event=None):
        close_dialog()
        if hasattr(app, 'check_updates'):
            await app.check_updates(manual=True)

    dialog = ft.AlertDialog(
        modal=False,
        alignment=ft.Alignment.CENTER,
        content=content,
        actions=[
            button('🔄 Buscar actualizaciones', app.bind(check_updates)),
            button('Cerrar', app.bind(dismiss), primary=False),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog


def show_about_dialog(app):
    """Muestra el diálogo modal de Acerca de en la página activa."""
    dialog = build_about_dialog(app)
    if hasattr(app.page, 'show_dialog'):
        app.page.show_dialog(dialog)
    app.page.update()
    return dialog
