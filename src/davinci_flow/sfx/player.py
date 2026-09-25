"""Reproductor de vista previa de audio ligero y nativo para Windows y entornos de escritorio."""

from __future__ import annotations

import ctypes
import os
import sys
import threading
from pathlib import Path


class SoundPlayer:
    """Reproductor de preescucha no bloqueante para efectos de sonido (SFX)."""

    def __init__(self, alias: str = "dvf_sfx_preview") -> None:
        self.alias = alias
        self._current_path: str | None = None
        self._lock = threading.Lock()

    @property
    def current_path(self) -> str | None:
        return self._current_path

    def _get_short_path(self, path_str: str) -> str:
        """Obtiene la ruta 8.3 de Windows para evitar problemas con acentos o espacios en MCI."""
        if sys.platform != "win32":
            return path_str
        try:
            buffer = ctypes.create_unicode_buffer(500)
            ctypes.windll.kernel32.GetShortPathNameW(path_str, buffer, 500)
            return buffer.value or path_str
        except Exception:
            return path_str

    def play(self, file_path: str | Path) -> bool:
        """Reproduce un archivo de audio (.mp3, .wav, etc.) de forma asíncrona."""
        resolved = str(Path(file_path).resolve())
        if not os.path.isfile(resolved):
            return False

        with self._lock:
            self.stop()
            self._current_path = resolved

            if sys.platform == "win32":
                try:
                    short_path = self._get_short_path(resolved)
                    mci = ctypes.windll.winmm.mciSendStringW
                    mci(f"close {self.alias}", None, 0, None)
                    
                    # Intentar abrir como mpegvideo (para mp3/aac) y fallback general
                    err = mci(f'open "{short_path}" type mpegvideo alias {self.alias}', None, 0, None)
                    if err != 0:
                        err = mci(f'open "{short_path}" alias {self.alias}', None, 0, None)
                    
                    if err == 0:
                        mci(f"play {self.alias}", None, 0, None)
                        return True
                    return False
                except Exception:
                    return False
            elif sys.platform == "darwin":
                try:
                    import subprocess
                    subprocess.Popen(["afplay", resolved])
                    return True
                except Exception:
                    return False
            return False

    def stop(self) -> None:
        """Detiene la reproducción activa."""
        with self._lock:
            if sys.platform == "win32":
                try:
                    mci = ctypes.windll.winmm.mciSendStringW
                    mci(f"stop {self.alias}", None, 0, None)
                    mci(f"close {self.alias}", None, 0, None)
                except Exception:
                    pass
            self._current_path = None

    def is_playing_path(self, file_path: str | Path) -> bool:
        """Comprueba si el archivo dado es el que está actualmente en reproducción."""
        if not self._current_path:
            return False
        return str(Path(file_path).resolve()) == self._current_path


# Instancia compartida global para la UI
global_sound_player = SoundPlayer()
