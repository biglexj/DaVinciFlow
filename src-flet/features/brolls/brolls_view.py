"""Vista especializada de B-Rolls y recursos visuales complementarios."""

from pathlib import Path
import flet as ft

from shared.components import ACCENT, CARD, FIELD, LINE, MUTED, TEXT, button, card, field, text


class BRollsView:
    def __init__(self, app):
        self.app, self.controller = app, app.controller
        self.query = field("Buscar en B-Rolls", expand=True, on_change=self.app.bind(self.search))
        self.list_column = ft.Column(spacing=6)
        self.summary = text("Configura carpetas de B-Roll para ver tus recursos visuales.", color=MUTED, size=12)
        self.folders_card = card(
            ft.Row([
                ft.Icon(ft.Icons.VIDEO_LIBRARY_ROUNDED, color=ACCENT, size=18),
                self.summary,
                ft.Container(expand=True),
                button("Añadir carpeta", self.app.bind(self.browse_folder), ft.Icons.CREATE_NEW_FOLDER_OUTLINED),
                button("Reindexar", self.app.bind(self.reindex), ft.Icons.REFRESH, primary=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10,
        )

        self.content = ft.Column([
            text("B-Rolls y Material Complementario", 22, weight=ft.FontWeight.W_600),
            text("Clips de apoyo, imágenes y recursos visuales listos para ilustrar ideas clave en tu montaje.", color=MUTED),
            self.folders_card,
            ft.Row([self.query]),
            card(self.list_column, padding=10),
        ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.refresh()

    async def browse_folder(self):
        self.app.library.category = "visuals"
        await self.app.library.browse()
        self.refresh()

    async def reindex(self):
        self.app.library.category = "visuals"
        await self.app.library.scan()
        self.refresh()

    async def search(self):
        self.refresh()
        self.app.page.update()

    def _render_broll_item(self, item_path: Path):
        ext = item_path.suffix.lower()
        is_video = ext in (".mp4", ".mov", ".mkv", ".avi", ".webm")
        icon = ft.Icons.MOVIE_OUTLINED if is_video else ft.Icons.IMAGE_OUTLINED
        type_label = "Vídeo" if is_video else "Imagen"
        badge_bg = "#16282B" if is_video else "#2A1F2D"
        badge_color = "#6FE3F5" if is_video else "#E594F7"

        size_mb = 0.0
        try:
            size_mb = item_path.stat().st_size / (1024 * 1024)
        except OSError:
            pass

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(icon, size=18, color=ACCENT),
                    ft.Column([
                        ft.Row([
                            text(item_path.stem, size=13, weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=text(type_label, size=10, weight=ft.FontWeight.W_500, color=badge_color),
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=10,
                                bgcolor=badge_bg,
                                border=ft.Border.all(0.6, badge_color),
                            ),
                            ft.Container(
                                content=text(ext.upper().replace(".", ""), size=10, color=MUTED),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4,
                                bgcolor="#161B1E",
                            ),
                        ], spacing=8),
                        text(str(item_path), size=11, color=MUTED, selectable=True),
                    ], spacing=2),
                ], spacing=10),
                text(f"{size_mb:.1f} MB" if size_mb > 0 else "", size=11, color=MUTED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor="#14181B",
            border=ft.Border.all(1, LINE),
        )

    def refresh(self):
        query = self.query.value.strip().lower()
        raw_folders = self.controller.preferences.paths.get("visuals", "")
        folders = [p.strip() for p in raw_folders.split(";") if p.strip()]

        matched_files = []
        valid_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".png", ".jpg", ".jpeg", ".webp"}

        for fld in folders:
            p = Path(fld)
            if not p.is_dir():
                continue
            try:
                # Si no hay búsqueda, solo listar archivos superficiales para evitar escanear terabytes de anime
                iterator = p.rglob("*") if query else p.glob("*")
                for file_path in iterator:
                    if file_path.suffix.lower() in valid_extensions and file_path.is_file():
                        if not query or query in file_path.name.lower():
                            matched_files.append(file_path)
                            if len(matched_files) >= (40 if query else 20):
                                break
            except OSError:
                continue
            if len(matched_files) >= (40 if query else 20):
                break

        matched_files.sort(key=lambda x: x.name.lower())
        count = len(matched_files)
        if query:
            self.summary.value = f"{len(folders)} carpetas configuradas · Mostrando {count} resultados para '{query}'."
        else:
            self.summary.value = f"{len(folders)} carpetas configuradas · Vista previa rápida (usa el buscador para clips específicos)."

        if not matched_files:
            empty_msg = (
                f"No se encontraron clips que coincidan con '{query}'." if query
                else ("No hay archivos visuales en la raíz de las carpetas configuradas. Usa el buscador superior para explorar subcarpetas." if folders
                      else "No hay carpetas de B-Roll añadidas. Pulsa '+ Añadir carpeta' para indexar tus clips.")
            )
            self.list_column.controls = [
                ft.Container(
                    content=text(empty_msg, color=MUTED, size=12),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            ]
        else:
            self.list_column.controls = [self._render_broll_item(f) for f in matched_files]
