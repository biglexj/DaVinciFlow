"""Reproducción de un vídeo dentro de su ficha, con una sola vista activa."""

from pathlib import Path

import flet as ft

from davinci_flow.editorial.model import EditorialError
from shared.components import ACCENT, TEXT


class InlineVideoPreview:
    def __init__(self, app):
        self.app = app
        self.player = self.host = self.poster = self.button = None
        self.path = None
        self.is_playing = False

    async def toggle(self, path, host, poster, button):
        import flet_video as ftv

        if not Path(path).is_file():
            raise EditorialError('No se encontró el vídeo. Vuelve a indexar su carpeta.')
        if self.player is not None and self.host is host:
            if self.is_playing:
                await self.player.pause()
            else:
                await self.player.play()
            self.is_playing = not self.is_playing
            self._mark()
            return
        await self.stop()
        self.host, self.poster, self.button = host, poster, button
        self.path, self.is_playing = str(path), True
        self.player = ftv.Video(
            playlist=[ftv.VideoMedia(Path(path).as_uri())], autoplay=True,
            controls=None, wakelock=False, fit=ft.BoxFit.CONTAIN,
            # La salida acelerada de Flet/MPV cerraba el cliente de Windows
            # al retirar fichas con H.264 reales; estas previsualizaciones usan CPU.
            configuration=ftv.VideoConfiguration(
                enable_hardware_acceleration=False, hardware_decoding_api='no',
            ),
            on_complete=self._complete, on_error=self._error,
        )
        host.content = self.player
        self._mark()

    def _mark(self):
        self.button.icon = ft.Icons.PAUSE_ROUNDED if self.is_playing else ft.Icons.PLAY_ARROW_ROUNDED
        self.button.icon_color = ACCENT if self.is_playing else TEXT
        self.button.tooltip = 'Pausar' if self.is_playing else 'Reproducir vídeo'

    def _reset(self):
        if self.host is not None:
            self.host.content = self.poster
        self.is_playing = False
        if self.button is not None:
            self._mark()
        self.player = self.host = self.poster = self.button = None
        self.path = None

    async def stop(self):
        if self.player is not None:
            try:
                await self.player.pause()
            finally:
                self._reset()

    def _complete(self, event):
        if event.control is self.player and event.data is True:
            self._reset()
            self.app.page.update()

    def _error(self, event):
        if event.control is self.player:
            self._reset()
            self.app.notify('No se pudo reproducir este vídeo.')
            self.app.page.update()
