"""Conexión controlada con la API local de DaVinci Resolve."""

import importlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from davinci_flow.errors import ResolveConnectionError


@dataclass(frozen=True, slots=True)
class ResolveSession:
    """Objetos activos necesarios para operar sobre una línea de tiempo."""

    resolve: Any
    project: Any
    timeline: Any


def _is_resolve_running() -> bool:
    """Evita cargar la biblioteca nativa cuando Resolve está cerrado."""
    if sys.platform == "win32":
        command = [
            "tasklist",
            "/FI",
            "IMAGENAME eq Resolve.exe",
            "/NH",
            "/FO",
            "CSV",
        ]
        expected_name = "resolve.exe"
    elif sys.platform == "darwin":
        command = ["pgrep", "-x", "Resolve"]
        expected_name = ""
    else:
        command = ["pgrep", "-x", "resolve"]
        expected_name = ""

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if result.returncode != 0:
        return False
    return expected_name in result.stdout.casefold() if expected_name else True


def _module_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    configured_api = os.environ.get("RESOLVE_SCRIPT_API")
    if configured_api:
        candidates.append(Path(configured_api) / "Modules")

    if sys.platform == "win32":
        program_data = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
        candidates.append(
            program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Developer"
            / "Scripting"
            / "Modules"
        )
    elif sys.platform == "darwin":
        candidates.append(
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
        )
    else:
        candidates.append(Path("/opt/resolve/Developer/Scripting/Modules"))

    return tuple(candidates)


def _load_resolve_module() -> ModuleType:
    try:
        return importlib.import_module("DaVinciResolveScript")
    except ModuleNotFoundError:
        pass

    for candidate in _module_candidates():
        if not candidate.is_dir():
            continue
        candidate_text = str(candidate)
        if candidate_text not in sys.path:
            sys.path.insert(0, candidate_text)
        try:
            return importlib.import_module("DaVinciResolveScript")
        except ModuleNotFoundError:
            continue

    raise ResolveConnectionError(
        "No se encontró DaVinciResolveScript. Comprueba RESOLVE_SCRIPT_API o la instalación de Resolve."
    )


def _validate_external_python_runtime() -> None:
    """Evita cargar una ABI nativa incompatible, que cerraría Python sin excepción recuperable."""
    if sys.platform == "win32" and sys.version_info[:2] != (3, 13):
        current = f"{sys.version_info[0]}.{sys.version_info[1]}"
        raise ResolveConnectionError(
            "DaVinci Resolve 21 en este equipo requiere Python 3.13 de 64 bits para el scripting externo "
            f"(runtime actual: Python {current}). Ejecuta con Python 3.13 o abre DaVinci Flow desde Resolve."
        )


def connect_to_resolve(resolve_instance: Any = None) -> ResolveSession:
    """Obtiene el proyecto y la línea de tiempo activos sin modificarlos."""
    resolve = resolve_instance

    # Si se ejecuta dentro de DaVinci Resolve, recuperar resolve desde el contexto
    if resolve is None:
        main_mod = sys.modules.get("__main__")
        if main_mod and hasattr(main_mod, "resolve"):
            resolve = getattr(main_mod, "resolve")
        elif hasattr(__builtins__, "resolve"):
            resolve = getattr(__builtins__, "resolve")

    if resolve is None:
        if not _is_resolve_running():
            raise ResolveConnectionError(
                "DaVinci Resolve no está en ejecución. Ábrelo antes de iniciar DaVinci Flow."
            )

        _validate_external_python_runtime()
        module = _load_resolve_module()
        resolve = module.scriptapp("Resolve")
        if resolve is None:
            raise ResolveConnectionError(
                "DaVinci Resolve no respondió. Ábrelo y habilita el acceso local al scripting."
            )

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    if project is None:
        raise ResolveConnectionError("No hay un proyecto activo en DaVinci Resolve.")

    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise ResolveConnectionError("El proyecto activo no tiene una línea de tiempo seleccionada.")

    return ResolveSession(resolve=resolve, project=project, timeline=timeline)
