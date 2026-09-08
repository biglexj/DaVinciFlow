"""Diseño compartido del espacio de trabajo Flet."""

import flet as ft

BG = '#121518'
SIDE = '#101214'
CARD = '#1B2024'
FIELD = '#14181C'
LINE = '#30373C'
TEXT = '#EDF2F3'
MUTED = '#ACB7BD'
ACCENT = '#00C7B1'

MODES = {'highlights': 'Énfasis selectivo', 'captions': 'Subtítulos completos'}
FORMATS = {'auto': 'Según la secuencia', 'horizontal': 'Horizontal', 'vertical': 'Vertical'}
DENSITIES = {'sparse': 'Pocos rótulos', 'balanced': 'Equilibrado', 'dense': 'Más rótulos'}


def text(value, size=12, color=TEXT, **kwargs):
    return ft.Text(value, size=size, color=color, **kwargs)


def field(label, value='', width=None, **kwargs):
    return ft.TextField(label=label, value=value, width=width, text_size=13, dense=True,
        border_radius=9, filled=True, fill_color=FIELD, border_color=LINE,
        focused_border_color=ACCENT, cursor_color=ACCENT, color=TEXT,
        label_style=ft.TextStyle(size=12, color=MUTED), content_padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        **kwargs)


def select(label, values, value=None, width=190, **kwargs):
    return ft.Dropdown(label=label, value=value, width=width,
        options=[ft.DropdownOption(key=k, text=v) for k, v in values.items()],
        text_size=12, dense=True, border_radius=9, filled=True, fill_color=FIELD,
        border_color=LINE, focused_border_color=ACCENT, color=TEXT,
        label_style=ft.TextStyle(size=12, color=MUTED), content_padding=12,
        menu_height=320, **kwargs)


def button(label, callback, icon=None, primary=False, **kwargs):
    return ft.Button(label, icon=icon, on_click=callback,
        style=ft.ButtonStyle(bgcolor=ACCENT if primary else '#293136', color=SIDE if primary else TEXT,
            shape=ft.RoundedRectangleBorder(radius=9), padding=ft.Padding.symmetric(horizontal=14, vertical=11),
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.W_600)),
        elevation=0, **kwargs)


def card(content, padding=14, **kwargs):
    return ft.Container(content=content, padding=padding, bgcolor=CARD,
                        border=ft.Border.all(1, LINE), border_radius=12, **kwargs)


def source_label(template):
    if template.source == 'media_pool':
        return 'Proyecto · Fusion'
    if 'basic_titles' in template.locator:
        return 'Text+ básico'
    return 'Instalado / archivo'


def scroll_table(table, width=1080, height=None, expand=True):
    """Cada eje tiene su propio viewport acotado y barra visible según desplazamiento."""
    return ft.Container(
        height=height,
        expand=expand,
        bgcolor=CARD,
        content=ft.Row(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(width=width, content=ft.Column([table], scroll=ft.ScrollMode.AUTO, expand=True))
            ],
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        border_radius=10,
        border=ft.Border.all(1, LINE),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
