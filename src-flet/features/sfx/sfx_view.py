"""Vista especializada de Efectos de Sonido (SFX) para DaVinci Flow."""

import flet as ft

from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS
from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, TEXT, button, card, field, select, text


class SFXView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.category_filter = select(
            "Filtrar categoría",
            {
                "all": "Todos los sonidos",
                "pop": "Pops y burbujas",
                "whoosh": "Whooshes y barridos",
                "click": "Clicks y tecnología",
                "bell": "Campanas y tonos",
                "riser": "Risers y tensión",
                "glitch": "Glitches digitales",
            },
            "all",
            200,
            on_select=self.app.bind(self.filter_sfx),
        )
        self.track_name = field("Pista SFX", "DF_SFX", width=120)
        self.anticipation = field("Anticipación (frames)", "-3", width=160, hint_text="Disparo previo al subtítulo")
        self.list_column = ft.Column(spacing=8)
        self.usage_summary = text("Sin propuesta activa para contabilizar uso.", color=MUTED, size=12)

        config_card = card(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TUNE_ROUNDED, color=ACCENT, size=18),
                    text("Ajustes de inyección sonora en Resolve:", size=13, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Row([
                    self.track_name,
                    self.anticipation,
                    button(
                        "Ir a Biblioteca SFX",
                        self.app.bind(self.go_to_library_sfx),
                        ft.Icons.FOLDER_OPEN_OUTLINED,
                        tooltip="Configurar carpetas adicionales de efectos de sonido",
                    ),
                ], wrap=True, spacing=10, run_spacing=8),
            ], spacing=10),
            padding=12,
        )

        self.content = ft.Column([
            text("Efectos de Sonido (SFX)", 22, weight=ft.FontWeight.W_600),
            text("Acentos auditivos procedurales sincronizados con anticipación exacta a cada subtítulo clave.", color=MUTED),
            config_card,
            card(ft.Row([
                ft.Icon(ft.Icons.GRAPHIC_EQ_ROUNDED, color=ACCENT, size=18),
                self.usage_summary,
            ], spacing=8), padding=10),
            ft.Row([self.category_filter]),
            card(self.list_column, padding=10),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.refresh()

    async def go_to_library_sfx(self):
        self.app.library.category = "sfx"
        self.app.library.update_folders_ui()
        self.app.library.refresh()
        await self.app.navigate("library")

    async def filter_sfx(self):
        self.refresh()
        self.app.page.update()

    def _render_sfx_item(self, asset):
        cat_labels = {
            "whoosh": ("Whoosh", "#1A2E35", "#325E6D", "#7CE0FF"),
            "pop": ("Pop", "#2B2816", "#61571F", "#FFE066"),
            "bell": ("Campana", "#2D1D30", "#63386B", "#E3A3ED"),
            "click": ("Click", "#1C2428", "#334149", "#A6B5BF"),
            "riser": ("Tensión", "#301A1A", "#692E2E", "#FF8A8A"),
            "glitch": ("Glitch", "#172922", "#2B5E4A", "#6CE6B4"),
        }
        badge_info = cat_labels.get(asset.category, (asset.category.capitalize(), "#1C2428", LINE, TEXT))
        badge_name, badge_bg, badge_border, badge_color = badge_info

        intents_str = ", ".join(asset.allowed_intents)

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, size=18, color=ACCENT),
                    ft.Column([
                        ft.Row([
                            text(asset.name, size=13, weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=text(badge_name, size=10, weight=ft.FontWeight.W_500, color=badge_color),
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=10,
                                bgcolor=badge_bg,
                                border=ft.Border.all(0.6, badge_border),
                            ),
                        ], spacing=8),
                        text(f"Duración: {asset.duration_seconds:.2f}s · Ganancia: {asset.recommended_gain_db:g} dB · Usos: {intents_str}",
                             size=11, color=MUTED),
                    ], spacing=2),
                ], spacing=10),
                ft.Container(
                    content=text(f"{asset.duration_seconds:.2f}s", size=11, color=MUTED),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                    bgcolor="#111518",
                    border=ft.Border.all(0.6, LINE),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor="#14181B",
            border=ft.Border.all(1, LINE),
        )

    def refresh(self):
        filter_val = self.category_filter.value
        items = []
        for asset in DEFAULT_SFX_ASSETS:
            if filter_val != "all" and asset.category != filter_val:
                continue
            items.append(self._render_sfx_item(asset))
        self.list_column.controls = items

        proposal = self.controller.proposal
        if proposal:
            sfx_count = sum(1 for d in proposal.decisions if d.enabled and getattr(d, "sfx", None))
            total = len(proposal.decisions)
            self.usage_summary.value = f"Propuesta activa: {sfx_count} de {total} subtítulos tienen acento SFX asignado en DF_SFX."
        else:
            self.usage_summary.value = "Genera o revisa una propuesta en el Editor para auditar el uso de SFX en tu secuencia."
