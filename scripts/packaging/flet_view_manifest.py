"""Manifiesto de vistas de la interfaz para el bundle congelado.

PyInstaller solo detecta imports estaticos. Las vistas de DaVinci Flow se
importan en tiempo de ejecucion (`src-flet/app/views.py` usa `import_module`),
de modo que el ejecutable instalado debe declararlas de forma explicita o
muere al arrancar con `ModuleNotFoundError`.

Este modulo es la fuente de ese manifiesto: lo usan la compilacion del bundle
(`packaging/windows/launcher/DaVinciFlow.spec`) y las pruebas, para que anadir
una vista nueva no requiera tocar el empaquetado.
"""

from __future__ import annotations

import ast
from pathlib import Path

FLET_ROOT = Path("src-flet")
VIEWS_MODULE = Path("app") / "views.py"


def view_modules(repo_root: Path) -> list[str]:
    """Modulos de las vistas declarados en `src-flet/app/views.py`.

    Se leen del codigo fuente y no se importan: la lista refleja exactamente
    lo que la aplicacion registrara en `VIEW_TYPES`.
    """
    views_path = repo_root / FLET_ROOT / VIEWS_MODULE
    tree = ast.parse(views_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "VIEW_TYPES" for target in node.targets):
            continue
        for entry in node.value.values:
            module = entry.elts[0]
            if isinstance(module, ast.Constant) and isinstance(module.value, str):
                modules.append(module.value)
    if not modules:
        raise SystemExit(f"No se pudo leer VIEW_TYPES desde {views_path}.")
    return modules


def namespace_packages(repo_root: Path) -> list[str]:
    """Paquetes de `src-flet` sin `__init__.py`.

    Un paquete sin `__init__.py` es un «namespace package»: Python lo admite,
    pero PyInstaller no lo recorre al recoger los submodulos, y la vista
    correspondiente faltaria en el bundle.
    """
    root = repo_root / FLET_ROOT
    missing: list[str] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_dir() or candidate.name == "__pycache__":
            continue
        if not any(child.suffix == ".py" for child in candidate.iterdir()):
            continue
        if not (candidate / "__init__.py").is_file():
            missing.append(candidate.relative_to(root).as_posix())
    return missing
