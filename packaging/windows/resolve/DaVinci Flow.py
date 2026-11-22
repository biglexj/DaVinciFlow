#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Iniciador de DaVinci Flow para el menu Scripts de DaVinci Resolve.

Este archivo lo instala el instalador de DaVinci Flow en la carpeta Utility
de scripts del usuario de Resolve (`%APPDATA%\\Blackmagic Design\\DaVinci
Resolve\\Support\\Fusion\\Scripts\\Utility`) y aparece en el menu
`Workspace > Scripts`.

Es autonomo: solo usa la biblioteca estandar y busca el ejecutable instalado
de DaVinci Flow. No depende del repositorio de desarrollo ni de sus entornos
virtuales, y nunca deja la sesion de Resolve bloqueada: el ejecutable se
lanza como proceso independiente.
"""

import os
import subprocess
import traceback
from pathlib import Path

LOG_FILE = Path.home() / ".davinci_flow_error.log"


def _find_installed_exe():
    """Localiza el ejecutable instalado de DaVinci Flow."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
        / "Programs"
        / "DaVinciFlow"
        / "DaVinciFlow.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "DaVinciFlow"
        / "DaVinciFlow.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "DaVinciFlow"
        / "DaVinciFlow.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def main():
    installed_exe = _find_installed_exe()
    if not installed_exe:
        raise FileNotFoundError(
            "DaVinci Flow no esta instalado. Reinstala la aplicacion y vuelve a intentar."
        )
    subprocess.Popen(
        [str(installed_exe)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write("Error al iniciar DaVinci Flow:\n%s\n\n" % traceback.format_exc())
        except Exception:
            pass
        print("Error al iniciar DaVinci Flow: %s (ver %s)" % (err, LOG_FILE))
