"""Adaptación localizada del cliente Flet."""

import asyncio
from contextlib import contextmanager
import platform
import sys


class ThreadWaitProcess:
    def __init__(self, process):
        self.process = process

    async def wait(self):
        return await asyncio.to_thread(self.process.wait)


@contextmanager
def desktop_runtime():
    if platform.python_implementation() != 'PyPy' or sys.platform != 'win32':
        yield
        return
    import flet_desktop
    original = flet_desktop.open_flet_view_async
    async def open_view(page_url, assets_dir, hidden):
        process, pid_file = await asyncio.to_thread(flet_desktop.open_flet_view, page_url, assets_dir, hidden)
        return ThreadWaitProcess(process), pid_file
    flet_desktop.open_flet_view_async = open_view
    try:
        yield
    finally:
        flet_desktop.open_flet_view_async = original
