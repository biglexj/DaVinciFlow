"""Selector local centrado, sin servicios dependientes de CPython."""

import asyncio
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import flet as ft

from shared.components import ACCENT, MUTED, button, field, text


def get_system_drives():
    drives = []
    if sys.platform == 'win32':
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if (bitmask >> i) & 1:
                    drive = f"{chr(65 + i)}:\\"
                    if os.path.exists(drive):
                        drives.append(drive)
        except Exception:
            for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
    else:
        drives.append('/')
    return drives


def list_entries(directory, extensions=(), directories_only=False):
    allowed = {'.' + ext.lower().lstrip('.') for ext in extensions}
    entries = [p for p in directory.iterdir() if not p.name.startswith('.') and
               (p.is_dir() or not directories_only and (not allowed or p.suffix.lower() in allowed))]
    return sorted(entries, key=lambda p: (not p.is_dir(), p.name.casefold()))[:500]


class WorkspaceFilePicker:
    def __init__(self, app):
        self.app = app
        self.last_directory = Path.home() / 'Documents'
        if not self.last_directory.is_dir():
            self.last_directory = Path.home()

    async def pick_files(self, dialog_title='Abrir archivo', initial_directory=None, allowed_extensions=(), **kwargs):
        path = await self.choose(dialog_title, 'open', initial_directory, allowed_extensions)
        return [SimpleNamespace(path=path)] if path else []

    async def save_file(self, dialog_title='Guardar archivo', file_name='', initial_directory=None, allowed_extensions=(), **kwargs):
        path = await self.choose(dialog_title, 'save', initial_directory, allowed_extensions, file_name)
        if path and Path(path).exists():
            if not await self.app.confirm('Reemplazar archivo', f'Ya existe {Path(path).name}. ¿Reemplazarlo?'):
                return None
        return path

    async def get_directory_path(self, dialog_title='Elegir carpeta', initial_directory=None):
        return await self.choose(dialog_title, 'directory', initial_directory)

    async def choose(self, title, mode, initial_directory, extensions=(), file_name=''):
        future = asyncio.get_running_loop().create_future()
        current = Path(initial_directory).expanduser() if initial_directory else self.last_directory
        if not current.is_dir():
            current = self.last_directory
        path_field = field('Carpeta', str(current), expand=True)
        filename = field('Nombre del archivo', file_name, visible=mode != 'directory')
        entries = ft.ListView(height=225, spacing=2)
        message = text('', color=MUTED)
        drives = get_system_drives()

        async def finish(value):
            self.app.page.pop_dialog()
            if not future.done():
                future.set_result(value)
            self.app.page.update()

        async def cancel(event=None):
            await finish(None)

        def make_drive_button(drv):
            label = drv.rstrip('\\')
            async def click_drive(event, target=drv):
                await load(Path(target))
            return ft.TextButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.STORAGE, size=14, color=ACCENT if str(current).upper().startswith(drv.upper()) else MUTED),
                    text(label, size=12, color=ACCENT if str(current).upper().startswith(drv.upper()) else MUTED),
                ], spacing=4, tight=True),
                tooltip=f'Disco {drv}',
                on_click=click_drive,
            )

        drives_controls = [make_drive_button(d) for d in drives]
        drives_row = ft.Row([
            text('Unidades:', size=12, color=MUTED),
            *drives_controls,
        ], spacing=4, scroll=ft.ScrollMode.ADAPTIVE) if len(drives) > 1 else ft.Container()

        new_folder_field = field('Nombre de la nueva carpeta', '', expand=True)

        async def cancel_new_folder(event=None):
            new_folder_box.visible = False
            new_folder_field.value = ''
            self.app.page.update()

        async def create_new_folder(event=None):
            folder_name = new_folder_field.value.strip()
            if not folder_name:
                message.value = 'Escribe el nombre de la carpeta.'
                self.app.page.update()
                return
            target_dir = current / folder_name
            try:
                target_dir.mkdir(parents=True, exist_ok=False)
                new_folder_box.visible = False
                new_folder_field.value = ''
                await load(target_dir)
            except FileExistsError:
                message.value = f'La carpeta "{folder_name}" ya existe.'
            except OSError as error:
                message.value = f'No se pudo crear la carpeta: {error}'
            self.app.page.update()

        new_folder_field.on_submit = create_new_folder
        new_folder_box = ft.Container(
            content=ft.Row([
                new_folder_field,
                button('Crear', create_new_folder, ft.Icons.CHECK, primary=True),
                button('Cancelar', cancel_new_folder),
            ], spacing=8),
            visible=False,
            padding=ft.Padding.only(top=2, bottom=2),
        )

        async def toggle_new_folder(event=None):
            new_folder_box.visible = not new_folder_box.visible
            if new_folder_box.visible:
                new_folder_field.value = ''
            self.app.page.update()

        async def load(directory):
            nonlocal current
            try:
                directory = directory.expanduser().resolve()
                files = await asyncio.to_thread(list_entries, directory, extensions, mode == 'directory')
                current = directory
                path_field.value = str(directory)
                if len(drives) > 1:
                    for btn, drv in zip(drives_controls, drives):
                        is_active = str(directory).upper().startswith(drv.upper())
                        btn.content.controls[0].color = ACCENT if is_active else MUTED
                        btn.content.controls[1].color = ACCENT if is_active else MUTED
                entries.controls = []
                for item in files:
                    async def select_item(event, target=item):
                        if target.is_dir():
                            await load(target)
                        else:
                            filename.value = target.name
                        self.app.page.update()
                    entries.controls.append(ft.TextButton(content=ft.Row([
                        ft.Icon(ft.Icons.FOLDER_OUTLINED if item.is_dir() else ft.Icons.DESCRIPTION_OUTLINED,
                                color=ACCENT if item.is_dir() else MUTED, size=18),
                        text(item.name, size=13, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=item.name)
                    ]), on_click=select_item))
                message.value = 'Carpeta vacía.' if not files else f'{len(files)} elementos' + (' · Usa una carpeta más concreta para ver más.' if len(files) == 500 else '')
            except (OSError, ValueError) as error:
                message.value = f'No se pudo abrir la carpeta: {error}'
            self.app.page.update()

        async def navigate(event=None):
            await load(Path(path_field.value))
            self.app.page.update()

        async def up(event=None):
            if current.parent == current:
                path_field.value = 'Este equipo'
                entries.controls = []
                for drv in drives:
                    async def select_drive(event, target=drv):
                        await load(Path(target))
                    entries.controls.append(ft.TextButton(content=ft.Row([
                        ft.Icon(ft.Icons.STORAGE, color=ACCENT, size=18),
                        text(f'Disco local ({drv})', size=13, expand=True),
                    ]), on_click=select_drive))
                message.value = f'{len(drives)} unidades disponibles.'
                self.app.page.update()
                return
            await load(current.parent)
            self.app.page.update()

        async def accept(event=None):
            try:
                directory = Path(path_field.value).expanduser().resolve()
                if not directory.is_dir():
                    raise ValueError('La carpeta no existe.')
                target = directory if mode == 'directory' else directory / filename.value.strip()
                if mode != 'directory' and not filename.value.strip():
                    raise ValueError('Elige un archivo o escribe su nombre.')
                if mode == 'save' and extensions and not target.suffix:
                    target = target.with_suffix('.' + extensions[0])
                if mode != 'directory' and extensions and target.suffix.lower().lstrip('.') not in extensions:
                    raise ValueError('Selecciona un archivo ' + ', '.join('.' + ext for ext in extensions) + '.')
                if mode == 'open' and not target.is_file():
                    raise ValueError('El archivo no existe.')
                if mode == 'save' and (target.is_dir() or not target.parent.is_dir()):
                    raise ValueError('Elige una ubicación y un nombre de archivo válidos.')
                self.last_directory = directory
                await finish(str(target.resolve()))
            except (OSError, ValueError) as error:
                message.value = str(error)
                self.app.page.update()

        path_field.on_submit = navigate
        filename.on_submit = accept
        dialog = ft.AlertDialog(modal=True, alignment=ft.Alignment.CENTER,
            title=text(title, 18), content=ft.Container(ft.Column([
                ft.Row([
                    path_field,
                    ft.IconButton(ft.Icons.ARROW_UPWARD, tooltip='Carpeta superior', on_click=up),
                    ft.IconButton(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, tooltip='Nueva carpeta', on_click=toggle_new_folder),
                    button('Ir', navigate),
                ], spacing=6),
                new_folder_box,
                drives_row,
                entries, filename, message,
            ], tight=True, spacing=8), width=680), actions=[button('Cancelar', cancel),
                button('Guardar' if mode == 'save' else 'Elegir carpeta' if mode == 'directory' else 'Abrir', accept, primary=True)])
        await load(current)
        self.app.page.show_dialog(dialog)
        return await future
