# -*- mode: python ; coding: utf-8 -*-
"""Especificacion de PyInstaller para el ejecutable de escritorio de DaVinci Flow.

La consume `scripts/packaging/Build-Installer.ps1`. El bundle es
autocontenido: ademas del codigo de la app incluye el cliente de escritorio
de Flet, para que la primera ejecucion no dependa de una descarga.

Salida: un directorio `DaVinciFlow/` con `DaVinciFlow.exe` y `_internal/`.
Se instala completo en `{app}`.
"""

import importlib.util
import os
import sys
import tomllib
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
WINDOWS_DIR = SPEC_DIR.parent
ROOT = WINDOWS_DIR.parent.parent
BUILD_DIR = WINDOWS_DIR / "build"
CLIENT_ZIP = BUILD_DIR / "cache" / "flet-windows.zip"
LAUNCHER = SPEC_DIR / "DaVinciFlow.py"
RESOLVE_LAUNCHER = WINDOWS_DIR / "resolve" / "DaVinci Flow.py"
ICON = ROOT / "assets" / "branding" / "icons" / "icon-windows.ico"
PYTHON_ROOT = ROOT / "src"
FLET_ROOT = ROOT / "src-flet"

# --- Rutas resolubles durante la compilacion ---------------------------------
# El analisis de PyInstaller sigue imports estaticos. La interfaz importa sus
# vistas en tiempo de ejecucion (`app/views.py` usa `import_module`), asi que
# el bundle debe declararlas de forma explicita: sin esto, el ejecutable
# instalado muere al arrancar con `ModuleNotFoundError`.
#
# Ademas, `collect_all` necesita importar el paquete para recoger sus datos
# (las plantillas `.setting` de `davinci_flow.editorial.basic_titles`). Con las
# dos raices en `sys.path` y en `PYTHONPATH`, tanto el proceso de compilacion
# como los subprocesos aislados de PyInstaller las encuentran.
for _root in (PYTHON_ROOT, FLET_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
os.environ["PYTHONPATH"] = os.pathsep.join(
    [str(PYTHON_ROOT), str(FLET_ROOT), os.environ.get("PYTHONPATH", "")]
)


def _view_modules() -> list:
    """Modulos de las vistas declarados en `app/views.py`.

    El manifiesto vive en `scripts/packaging/flet_view_manifest.py` y lo
    comparten la compilacion y las pruebas: anadir una vista nueva no obliga
    a tocar este archivo.
    """
    manifest_path = ROOT / "scripts" / "packaging" / "flet_view_manifest.py"
    spec = importlib.util.spec_from_file_location("flet_view_manifest", manifest_path)
    manifest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manifest)
    return manifest.view_modules(ROOT)

if not CLIENT_ZIP.is_file():
    raise SystemExit(
        "Falta el cliente de escritorio de Flet (%s). Ejecuta "
        "scripts/packaging/Build-Installer.ps1 para preparar el staging."
        % CLIENT_ZIP
    )

# --- Version real leida de pyproject.toml -----------------------------------
with (ROOT / "pyproject.toml").open("rb") as handle:
    _version = tomllib.load(handle)["project"]["version"]
_version_tuple = tuple(int(part) for part in _version.split("."))
while len(_version_tuple) < 4:
    _version_tuple = _version_tuple + (0,)

BUILD_DIR.mkdir(parents=True, exist_ok=True)
VERSION_FILE = BUILD_DIR / "version_info.txt"
VERSION_FILE.write_text(
    """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=%s,
    prodvers=%s,
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Biglex'),
         StringStruct('FileDescription', 'DaVinci Flow'),
         StringStruct('FileVersion', '%s'),
         StringStruct('InternalName', 'DaVinciFlow'),
         StringStruct('OriginalFilename', 'DaVinciFlow.exe'),
         StringStruct('ProductName', 'DaVinci Flow'),
         StringStruct('ProductVersion', '%s')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    % (
        _version_tuple,
        _version_tuple,
        _version,
        _version,
    ),
    encoding="utf-8",
)

datas = [
    (str(ROOT / "assets" / "branding" / "icons"), "assets/branding/icons"),
    (str(CLIENT_ZIP), "flet_desktop/app"),
]
binaries = []
hiddenimports = []

# Flet distribuye datos (icons.json, assets, plantillas) que se leen en
# tiempo de ejecucion: sin `collect_all` el cliente no encuentra sus
# archivos y la app falla al construir la interfaz.
from PyInstaller.utils.hooks import collect_all, collect_submodules

for _package in ("flet", "flet_desktop", "flet_video", "davinci_flow", "yt_dlp"):
    _datas, _binaries, _hidden = collect_all(_package)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden

# Las vistas y los modulos de la interfaz se importan en tiempo de ejecucion.
# Se declaran aqui para que el bundle los contenga.
hiddenimports += _view_modules()
for _package in ("app", "features", "shared"):
    hiddenimports += collect_submodules(_package)

# El lanzador del menu Scripts de DaVinci Resolve viaja dentro del bundle:
# la app instalada puede reinstalarlo sin depender del repositorio.
if RESOLVE_LAUNCHER.is_file():
    datas.append((str(RESOLVE_LAUNCHER), "packaging/windows/resolve"))

a = Analysis(
    [str(LAUNCHER)],
    pathex=[str(ROOT / "src"), str(ROOT / "src-flet")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "pydoc_data"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DaVinciFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=os.environ.get("DAVINCIFLOW_DEBUG_CONSOLE") == "1",
    disable_windowed_traceback=False,
    icon=str(ICON),
    version=str(VERSION_FILE),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DaVinciFlow",
)
