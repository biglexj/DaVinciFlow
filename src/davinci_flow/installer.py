"""Instalador del iniciador de DaVinci Flow en el menú Scripts de DaVinci Resolve."""

import os
import sys
from pathlib import Path

LAUNCHER_SCRIPT_NAME = "DaVinci Flow.py"


def get_resolve_scripts_directory(user_only: bool = True) -> Path:
    """Devuelve la ruta oficial del directorio de scripts de DaVinci Resolve en Windows/macOS."""
    if sys.platform == "win32":
        if user_only:
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                appdata = str(Path.home() / "AppData" / "Roaming")
            base = Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility"
        else:
            progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
            base = Path(progdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility"
    else:  # Linux
        base = Path.home() / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility"

    return base


def get_launcher_code(source_dir: Path | None = None) -> str:
    """Genera el código ejecutable mínimo del lanzador para el menú de Resolve."""
    if source_dir is None:
        source_dir = Path(__file__).resolve().parent.parent

    # Usar barras normales para evitar problemas de escape en cadenas
    source_dir_str = str(source_dir).replace("\\", "/")

    return f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"Iniciador de DaVinci Flow para el menú Scripts de DaVinci Resolve.\"\"\"

import sys
from pathlib import Path

# Inyectar la ruta de DaVinci Flow al entorno
DF_SRC_PATH = "{source_dir_str}"
if DF_SRC_PATH not in sys.path:
    sys.path.insert(0, DF_SRC_PATH)

try:
    from davinci_flow.ui import open_davinci_flow_ui
    open_davinci_flow_ui()
except Exception as err:
    print(f"Error al iniciar DaVinci Flow: {{err}}", file=sys.stderr)
    import traceback
    traceback.print_exc()
"""


def install_resolve_launcher(user_only: bool = True) -> Path:
    """Instala el archivo lanzador en la carpeta Utility de DaVinci Resolve."""
    scripts_dir = get_resolve_scripts_directory(user_only=user_only)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = scripts_dir / LAUNCHER_SCRIPT_NAME
    launcher_code = get_launcher_code()
    launcher_path.write_text(launcher_code, encoding="utf-8")
    return launcher_path


def uninstall_resolve_launcher(user_only: bool = True) -> bool:
    """Desinstala el archivo lanzador de DaVinci Resolve si existe."""
    scripts_dir = get_resolve_scripts_directory(user_only=user_only)
    launcher_path = scripts_dir / LAUNCHER_SCRIPT_NAME
    if launcher_path.exists():
        launcher_path.unlink()
        return True
    return False
