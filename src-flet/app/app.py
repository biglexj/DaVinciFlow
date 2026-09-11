"""Una ventana Flet; trabajo secuencial fuera del bucle de interfaz."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import platform
from pathlib import Path
import flet as ft

from davinci_flow.editorial.controller import EditorialController
from shared.components import ACCENT, BG, LINE, MUTED, SIDE, TEXT, button, text
from shared.path_picker import WorkspaceFilePicker
from app.instance import DesktopInstance
from app.runtime import desktop_runtime
from features.editor.editor_view import EditorView
from features.subtitles.subtitles_view import SubtitlesView
from features.catalog.catalog_view import CatalogView
from features.library.library_view import LibraryView
from features.settings.settings_view import SettingsView

BRANDING = Path(__file__).resolve().parents[2] / 'assets/branding/icons'


class DesktopApp:
    def __init__(self, page, controller=None):
        self.page = page
        self.controller = controller or EditorialController()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='davinci-flow')
        self.busy = False
        self.closing = False
        self.current = 'editor'
        page.title = 'DaVinci Flow — Editor y recursos'
        page.bgcolor = BG
        page.padding = 0
        page.spacing = 0
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(
            color_scheme_seed=ACCENT,
            font_family='Segoe UI',
            use_material3=True,
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_visibility=False,
                thickness=6,
                radius=4,
                thumb_color='#363E44',
                interactive=True,
            ),
        )
        page.window.width, page.window.height = 1180, 810
        page.window.min_width, page.window.min_height = 900, 640
        page.window.prevent_close = True
        page.window.icon = str(BRANDING / 'icon-windows.ico')
        page.window.on_event = self.window_event
        self.branding_path = BRANDING
        self.picker = WorkspaceFilePicker(self)
        self.identity = text('Sin secuencia capturada', color=MUTED, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)
        self.model = text(self.controller.preferences.model, color=ACCENT, no_wrap=True)
        self.status = text('Listo para abrir tu montaje.', color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.progress = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False, color=ACCENT)
        self.heading = text('Editor', 17, weight=ft.FontWeight.W_600)
        self.editor = EditorView(self)
        self.subtitles = SubtitlesView(self)
        self.catalog = CatalogView(self)
        self.library = LibraryView(self)
        self.settings = SettingsView(self)
        self.views = {
            'editor': self.editor,
            'subtitles': self.subtitles,
            'catalog': self.catalog,
            'library': self.library,
            'settings': self.settings,
        }
        self.nav = {}
        self.labels = {
            'editor': 'Editor',
            'subtitles': 'Corrección',
            'catalog': 'Plantillas',
            'library': 'Biblioteca',
            'settings': 'Ajustes',
        }
        icons = (
            ft.Icons.EDIT_NOTE_ROUNDED,
            ft.Icons.SPELLCHECK_ROUNDED,
            ft.Icons.TEXT_FIELDS_ROUNDED,
            ft.Icons.FOLDER_OUTLINED,
            ft.Icons.SETTINGS_OUTLINED,
        )
        for (key, label), icon in zip(self.labels.items(), icons):
            self.nav[key] = ft.Container(ft.Row([ft.Icon(icon, size=19, color=ACCENT if key == 'editor' else MUTED),
                text(label, 13, weight=ft.FontWeight.W_500)], spacing=10), padding=12, border_radius=9,
                bgcolor='#173A35' if key == 'editor' else None, on_click=self.bind(self.navigate, key))

        def on_about_hover(e):
            self.about_btn.bgcolor = '#173A35' if e.data == 'true' else None
            btn_content = self.about_btn.content
            if isinstance(btn_content, ft.Row) and len(btn_content.controls) >= 2:
                btn_content.controls[0].color = ACCENT if e.data == 'true' else MUTED
                btn_content.controls[1].color = TEXT if e.data == 'true' else MUTED
            self.page.update()

        self.about_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=18, color=MUTED),
                text('Acerca de', 13, weight=ft.FontWeight.W_500, color=MUTED),
            ], spacing=10),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=9,
            ink=True,
            tooltip='Acerca de DaVinci Flow',
            on_click=self.bind(self.show_about),
            on_hover=on_about_hover,
        )
        sidebar = ft.Container(width=168, bgcolor=SIDE, padding=ft.Padding.symmetric(horizontal=12, vertical=18),
            content=ft.Column([ft.Row([ft.Image(src=str(BRANDING / 'icon-transparent.png'), width=28, height=28),
                text('DaVinci Flow', 14, weight=ft.FontWeight.W_700)], spacing=5),
                text('Tu espacio creativo', 11, color=MUTED), ft.Container(height=5), self.identity,
                ft.Divider(color=LINE, height=22), *self.nav.values(),
                ft.Container(expand=True), self.about_btn], spacing=6))
        self.workspace = ft.Container(content=self.editor.content, expand=True, padding=ft.Padding.only(right=10))
        header = ft.Row([self.heading, ft.Container(expand=True),
            ft.Container(self.model, bgcolor='#153630', padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=7),
            ft.IconButton(icon=ft.Icons.PUSH_PIN_OUTLINED, icon_size=17, tooltip='Fijar al frente', on_click=self.bind(self.pin))], height=38)
        self.body = ft.Row([sidebar, ft.Container(ft.Column([header, self.workspace], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            expand=True, padding=ft.Padding.only(left=18, right=10, top=12, bottom=10))], expand=True, spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        self.footer = ft.Container(ft.Row([self.progress, self.status], spacing=10), padding=ft.Padding.symmetric(horizontal=18, vertical=9),
                                   border=ft.Border(top=ft.BorderSide(1, LINE)))
        self.latest_release = None
        self.checking_updates = False
        self.has_checked_updates = False
        self.toast_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=ACCENT, size=18)
        self.toast_text = text('✅ Estás en la última versión', 13, weight=ft.FontWeight.W_500, color=TEXT)
        self.toast_card = ft.Container(
            content=ft.Row([self.toast_icon, self.toast_text], spacing=8, alignment=ft.MainAxisAlignment.CENTER, tight=True),
            bgcolor='#182622',
            border=ft.Border.all(1, ACCENT),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            shadow=ft.BoxShadow(blur_radius=16, color='#80000000', offset=ft.Offset(0, 4)),
        )
        self.toast_overlay = ft.Container(
            content=self.toast_card,
            top=18,
            left=0,
            right=0,
            alignment=ft.Alignment.TOP_CENTER,
            visible=False,
            opacity=0.0,
            animate_opacity=300,
        )
        if hasattr(page, 'overlay'):
            page.overlay.append(self.toast_overlay)

        self.root = ft.Column([self.body, self.footer], spacing=0, expand=True)
        page.add(self.root)
        if hasattr(page, 'run_task'):
            page.run_task(self.editor.auto_capture_default)
            page.run_task(self.silent_update_check)

    def bind(self, callback, *arguments):
        async def handler(event=None):
            if self.busy:
                return
            try:
                result = callback(*arguments)
                if inspect.isawaitable(result):
                    await result
            except Exception as error:
                self.show_error(str(error))
            self.page.update()
        return handler

    async def run(self, message, operation):
        if self.busy:
            return None
        self.busy = True
        self.body.disabled = True
        self.progress.visible = True
        self.notify(message)
        self.page.update()
        try:
            result = await asyncio.get_running_loop().run_in_executor(self.executor, operation)
            self.notify('Acción completada.')
            return result
        except Exception as error:
            self.show_error(str(error))
            return None
        finally:
            self.busy = False
            self.body.disabled = False
            self.progress.visible = False
            self.page.update()

    def notify(self, message):
        self.status.value = message
        self.status.tooltip = message

    def show_error(self, message):
        self.notify(message)
        async def dismiss(event):
            self.page.pop_dialog()
            self.page.update()
        self.page.show_dialog(ft.AlertDialog(title=text('No se pudo completar la acción', 18),
            content=ft.Container(text(message, size=13, selectable=True), width=580), scrollable=True,
            alignment=ft.Alignment.CENTER, actions=[button('Entendido', dismiss)]))

    async def confirm(self, title, message):
        future = asyncio.get_running_loop().create_future()
        async def answer(value):
            self.page.pop_dialog()
            if not future.done():
                future.set_result(value)
        async def accept(event):
            await answer(True)
        async def cancel(event):
            await answer(False)
        self.page.show_dialog(ft.AlertDialog(modal=True, title=text(title, 18), content=text(message, size=13),
            alignment=ft.Alignment.CENTER, actions=[button('Volver', cancel), button('Continuar', accept, primary=True)]))
        return await future

    async def pick_file(self, title, extensions):
        files = await self.picker.pick_files(dialog_title=title, file_type=ft.FilePickerFileType.CUSTOM,
                                             allowed_extensions=extensions, allow_multiple=False)
        return files[0].path if files else None

    async def navigate(self, key):
        self.editor.sync_preferences()
        self.library.save_path()
        self.current = key
        self.workspace.content = self.views[key].content
        self.heading.value = 'Corrección de subtítulos' if key == 'subtitles' else self.labels[key]
        for item, control in self.nav.items():
            control.bgcolor = '#173A35' if item == key else None
            control.content.controls[0].color = ACCENT if item == key else MUTED
        if key == 'catalog':
            self.catalog.refresh()
        elif key == 'library':
            self.library.refresh()
        elif key == 'subtitles':
            self.subtitles.refresh()
        elif key == 'editor':
            self.editor.refresh()

    def refresh_identity(self):
        s = self.controller.snapshot
        self.identity.value = f'{s.project}\n{s.timeline}' if s else 'Sin secuencia capturada'
        self.identity.tooltip = self.identity.value
        self.model.value = self.controller.preferences.model

    async def pin(self):
        self.page.window.always_on_top = not self.page.window.always_on_top
        self.notify('Ventana fijada al frente.' if self.page.window.always_on_top else 'Ventana sin fijar.')

    def show_about(self):
        from features.about.about_dialog import show_about_dialog
        return show_about_dialog(self)

    async def silent_update_check(self):
        await asyncio.sleep(1.2)
        await self.check_updates(manual=False)

    async def show_toast(self, message, icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, duration=4.0):
        self.toast_text.value = message
        self.toast_icon.icon = icon
        self.toast_overlay.visible = True
        self.toast_overlay.opacity = 1.0
        try:
            self.toast_overlay.update()
        except Exception:
            pass
        self.page.update()

        async def fade():
            await asyncio.sleep(duration)
            self.toast_overlay.opacity = 0.0
            try:
                self.toast_overlay.update()
            except Exception:
                pass
            self.page.update()
            await asyncio.sleep(0.35)
            self.toast_overlay.visible = False
            try:
                self.toast_overlay.update()
            except Exception:
                pass
            self.page.update()

        if hasattr(self.page, 'run_task'):
            self.page.run_task(fade)
        else:
            asyncio.create_task(fade())

    async def check_updates(self, manual=False):
        if self.checking_updates:
            return self.latest_release
        self.checking_updates = True
        if manual:
            self.notify('Consultando GitHub Releases…')
        if hasattr(self, 'settings') and hasattr(self.settings, 'refresh_updates_ui'):
            self.settings.refresh_updates_ui()
        self.page.update()

        try:
            from davinci_flow.updater.checker import check_github_release
            release = await asyncio.get_running_loop().run_in_executor(self.executor, check_github_release)
            self.latest_release = release
            if release and release.is_newer:
                self.notify(f'🚀 Nueva versión v{release.version} disponible.')
                if manual and self.current != 'settings':
                    await self.navigate('settings')
            elif manual:
                from davinci_flow import __version__
                self.notify('Estás en la última versión.')
                await self.show_toast(f'✅ ¡Estás en la última versión! (v{__version__})')
            return release
        except Exception as error:
            if manual:
                self.notify(f'No se pudo comprobar actualizaciones: {error}')
            return None
        finally:
            self.checking_updates = False
            self.has_checked_updates = True
            if hasattr(self, 'settings') and hasattr(self.settings, 'refresh_updates_ui'):
                self.settings.refresh_updates_ui()
            self.page.update()

    async def window_event(self, event):
        if event.type != ft.WindowEventType.CLOSE or self.closing:
            return
        if self.busy:
            self.notify('Espera a que termine la operación antes de cerrar.')
            self.page.update()
            return
        self.closing = True
        try:
            if self.editor.form_changed() or self.controller.dirty:
                if not await self.confirm('Cambios sin guardar', 'Hay una revisión sin guardar en archivo. ¿Cerrar de todos modos?'):
                    return
            self.editor.sync_preferences()
            self.library.save_path()
            self.controller.save_preferences()
            self.executor.shutdown(wait=False)
            await self.page.window.destroy()
        except Exception as error:
            self.show_error(str(error))
        finally:
            self.closing = False


def open_desktop():
    instance = DesktopInstance()
    if not instance.acquire():
        return
    async def main(page):
        DesktopApp(page)
        await page.window.wait_until_ready_to_show()
        await page.window.center()
        page.window.visible = True
        page.update()
        async def activate_requests():
            while True:
                await asyncio.sleep(0.5)
                if instance.activation_requested():
                    page.window.minimized = False
                    page.update()
                    await page.window.to_front()
        page.run_task(activate_requests)
    try:
        with desktop_runtime():
            ft.run(main, view=ft.AppView.FLET_APP_HIDDEN, assets_dir=str(BRANDING))
    finally:
        instance.release()
