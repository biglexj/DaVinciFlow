"""Diálogo modal e información oficial de «Acerca de DaVinci Flow»."""

import inspect
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

    def launch(url):
        async def handler(event=None):
            result = app.page.launch_url(url)
            if inspect.isawaitable(result):
                await result
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
        width=620,
        content=ft.Column([
            ft.Container(height=3, bgcolor=ACCENT),
            ft.Row(header_items, alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            ft.Container(height=4),
            text('Desarrollado por biglexj (2026)', 13, weight=ft.FontWeight.W_600,
                 text_align=ft.TextAlign.CENTER, color=TEXT),
            text(
                'Automatización modular de subtítulos, Fusion y edición para DaVinci Resolve.',
                12, color=MUTED, text_align=ft.TextAlign.CENTER
            ),
            app.updates.content,
            ft.Divider(color=LINE, height=18),
            text('Apoyo oficial y canales de la comunidad', 14, weight=ft.FontWeight.BOLD),
            text('Gracias por usar DaVinci Flow. Puedes apoyar su desarrollo continuo a través de los canales oficiales.', 12, color=MUTED),
            ft.ResponsiveRow([
                ft.Container(col={'xs': 12, 'sm': 6}, content=ft.Button(
                    content=ft.Column([ft.Row([ft.Icon(ft.Icons.FAVORITE_BORDER), text('Donaciones oficiales', 13)]), text('Yape, Plin y transferencias', 11, color=MUTED)], spacing=6),
                    bgcolor=ft.Colors.with_opacity(0.16, ACCENT), color=TEXT, on_click=launch(DONATIONS_URL))),
                ft.Container(col={'xs': 12, 'sm': 6}, content=ft.Button(
                    content=ft.Column([ft.Row([ft.Icon(ft.Icons.COFFEE_ROUNDED), text('Buy Me a Coffee', 13)]), text('Apoya el desarrollo', 11, color=MUTED)], spacing=6),
                    bgcolor=ft.Colors.with_opacity(0.16, ACCENT), color=TEXT, on_click=launch(BUY_ME_A_COFFEE_URL))),
            ], spacing=8, run_spacing=8),
            ft.Row([
                ft.OutlinedButton('biglexj.com', icon=ft.Icons.PUBLIC, on_click=launch('https://biglexj.com/desarrollo/davinci-flow')),
                ft.OutlinedButton('@biglexj', icon=ft.Image(src=str(branding / 'github.svg'), width=16, height=16, color=TEXT) if branding else None, on_click=launch(GITHUB_URL)),
                ft.OutlinedButton('Repositorio', icon=ft.Icons.OPEN_IN_NEW, on_click=launch('https://github.com/biglexj/DaVinciFlow')),
                ft.OutlinedButton('Reportar un problema', icon=ft.Icons.BUG_REPORT, on_click=launch(FEEDBACK_URL)),
            ], wrap=True, spacing=8, run_spacing=8),
            ft.ExpansionTile(title=text('Licencia e información técnica', 12), leading=ft.Icon(ft.Icons.SHIELD_OUTLINED), controls=[
                text(f'Licencia MIT · biglexj · {platform.python_implementation()} · Flet v{ft.__version__}', 11, color=MUTED),
            ]),
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

    dialog = ft.AlertDialog(
        modal=False,
        title=text('Acerca de DaVinci Flow', 16, weight=ft.FontWeight.BOLD),
        barrier_color=SIDE,
        alignment=ft.Alignment.CENTER,
        content=content,
        scrollable=True,
        actions=[
            button('Cerrar', app.bind(dismiss), primary=False),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog


def show_about_dialog(app):
    """Muestra el diálogo modal de Acerca de en la página activa."""
    if app.about_dialog is not None and app.about_dialog.open:
        return app.about_dialog
    app.updates.refresh()
    dialog = app.about_dialog = build_about_dialog(app)
    if hasattr(app.page, 'show_dialog'):
        app.page.show_dialog(dialog)
    app.page.update()
    return dialog
