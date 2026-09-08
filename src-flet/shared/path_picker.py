"""Selector local centrado, sin servicios dependientes de CPython."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
import flet as ft

from shared.components import ACCENT, MUTED, button, field, text


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

        async def finish(value):
            self.app.page.pop_dialog()
            if not future.done():
                future.set_result(value)
            self.app.page.update()

        async def cancel(event=None):
            await finish(None)

        async def load(directory):
            nonlocal current
            try:
                directory = directory.expanduser().resolve()
                files = await asyncio.to_thread(list_entries, directory, extensions, mode == 'directory')
                current = directory
                path_field.value = str(directory)
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

        async def navigate(event=None):
            await load(Path(path_field.value))
            self.app.page.update()

        async def up(event=None):
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
                ft.Row([path_field, ft.IconButton(ft.Icons.ARROW_UPWARD, tooltip='Carpeta superior', on_click=up), button('Ir', navigate)]),
                entries, filename, message,
            ], tight=True, spacing=10), width=660), actions=[button('Cancelar', cancel),
                button('Guardar' if mode == 'save' else 'Elegir carpeta' if mode == 'directory' else 'Abrir', accept, primary=True)])
        await load(current)
        self.app.page.show_dialog(dialog)
        return await future
