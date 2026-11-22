"""Instalador del iniciador de DaVinci Flow en el menú Scripts de DaVinci Resolve."""

import os
import sys
from pathlib import Path

LAUNCHER_SCRIPT_NAME = "DaVinci Flow.py"
CANONICAL_LAUNCHER_RELATIVE = Path("packaging") / "windows" / "resolve" / LAUNCHER_SCRIPT_NAME


def find_installed_desktop() -> Path | None:
    if sys.platform != 'win32':
        return None
    bases = [Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local') / 'Programs',
             Path(os.environ.get('PROGRAMFILES') or 'C:/Program Files'),
             Path(os.environ.get('PROGRAMFILES(X86)') or 'C:/Program Files (x86)')]
    return next((p for base in bases if (p := base / 'DaVinciFlow/DaVinciFlow.exe').is_file()), None)


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


def find_canonical_launcher() -> Path | None:
    """Localiza el lanzador canónico que acompaña al proyecto.

    Vive en `packaging/windows/resolve/`. En desarrollo se lee del
    repositorio; en el ejecutable instalado viaja dentro del bundle. El
    instalador de Windows copia ese mismo archivo, de modo que ambos caminos
    de entrada ejecutan el mismo lanzador.
    """
    candidates = [Path(__file__).resolve().parents[2] / CANONICAL_LAUNCHER_RELATIVE]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / CANONICAL_LAUNCHER_RELATIVE)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def get_canonical_launcher_code() -> str | None:
    """Código del lanzador canónico, o None si no está disponible."""
    canonical = find_canonical_launcher()
    if canonical is None:
        return None
    return canonical.read_text(encoding="utf-8")


def get_launcher_code(source_dir: Path | None = None) -> str:
    """Genera el código ejecutable del lanzador para el menú de Resolve.

    Prevalece siempre la versión instalada estable de DaVinci Flow en el sistema
    para evitar que el trabajo activo en Resolve se vea afectado por cambios
    en el directorio de desarrollo.
    """
    if source_dir is None:
        source_dir = Path(__file__).resolve().parent.parent

    source_dir_str = str(source_dir).replace("\\", "/")

    return f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"Iniciador de DaVinci Flow para el menú Scripts de DaVinci Resolve.\"\"\"

import os
import subprocess
import sys
import traceback
from pathlib import Path


def _find_installed_exe() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Programs" / "DaVinciFlow" / "DaVinciFlow.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\\Program Files")) / "DaVinciFlow" / "DaVinciFlow.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")) / "DaVinciFlow" / "DaVinciFlow.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def main() -> None:
    installed_exe = _find_installed_exe()
    if installed_exe:
        # Prevalecer la versión instalada estable
        subprocess.Popen(
            [str(installed_exe)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return

    # Fallback si no hay versión instalada
    DF_SRC_PATH = {source_dir_str!r}
    if DF_SRC_PATH not in sys.path:
        sys.path.insert(0, DF_SRC_PATH)

    from davinci_flow.ui.desktop_launcher import launch_desktop as open_davinci_flow_ui
    open_davinci_flow_ui()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        log_file = Path.home() / ".davinci_flow_error.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"Error al iniciar DaVinci Flow:\\n{{traceback.format_exc()}}\\n\\n")
        print(f"Error al iniciar DaVinci Flow: {{err}} (ver {{log_file}})", file=sys.stderr)
        traceback.print_exc()
"""


def install_resolve_launcher(user_only: bool = True) -> Path:
    """Instala el archivo lanzador en la carpeta Utility de DaVinci Resolve.

    Con la aplicación instalada se usa el lanzador canónico, que solo busca
    el ejecutable instalado. Sin instalación previa se genera un lanzador con
    salida al código de desarrollo.
    """
    scripts_dir = get_resolve_scripts_directory(user_only=user_only)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = scripts_dir / LAUNCHER_SCRIPT_NAME
    installed = find_installed_desktop()
    if installed is not None and launcher_path.is_file():
        return launcher_path

    launcher_code = get_launcher_code()
    if installed is not None:
        launcher_code = get_canonical_launcher_code() or launcher_code
    if launcher_path.is_file() and launcher_path.read_text(encoding="utf-8") == launcher_code:
        return launcher_path
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
