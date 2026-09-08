# Separación de arquitectura Flet y Core (Patrón Tauri)

- Fecha: 2026-09-07
- Estado: EN EJECUCIÓN
- Proyecto: `D:\Proyectos\biglexj\DaVinciFlow`
- Autor: biglexj

## Objetivo

Desacoplar limpiamente el backend/lógica de automatización de DaVinci Resolve (`src/davinci_flow`) de la interfaz de usuario Flet (`src-flet`), adoptando el patrón de dos raíces estilo Tauri (`src/` para backend/core y `src-flet/` para frontend/diseño). Consolidar el proyecto en un único entorno virtual `.venv` con CPython 3.13 gestionado por `uv`, eliminando la sobrecarga de PyPy, los entornos redundantes y los intermediarios de subproceso.

## Alcance

1. **Frontend en `src-flet/`**:
   - Trasladar las vistas y componentes de `src/davinci_flow/ui/desktop/` a la nueva raíz `src-flet/`.
   - Crear `src-flet/main.py` como punto de entrada de la UI.
   - Organizar las vistas bajo `src-flet/views/` o módulos cohesivos.
2. **Backend puro en `src/davinci_flow/`**:
   - Mantener `src/davinci_flow/` intacto como paquete principal (`resolve`, `ai`, `editorial`, `generation`, `sfx`, `assets`, `subtitles`).
   - Cero dependencias de interfaz en el motor core.
3. **Consolidación en un solo `.venv`**:
   - Eliminar los entornos `.venv-pypy` y `.venv-resolve`.
   - Asegurar que `.venv` (CPython 3.13 64-bit) contenga `flet[desktop]` y las dependencias completas del proyecto vía `uv sync`.
4. **Scripts y lanzadores**:
   - Actualizar `scripts/start-desktop.ps1` y `scripts/setup-desktop.ps1` para usar únicamente `.venv` y `uv`.
   - Actualizar `installer.py` para que el script de menú de DaVinci Resolve invoque directamente `src-flet/main.py`.
5. **Limpieza y pruebas**:
   - Purgar `src/davinci_flow.egg-info/` y archivos residuales.
   - Adaptar las pruebas en `tests/test_desktop.py` para verificar la nueva estructura.
   - Constatar que la batería completa de 180+ pruebas pase al 100% en verde.
6. **Documentación Core (`Docs`)**:
   - Documentar la arquitectura y el estándar de proyectos Python en `D:\Proyectos\biglexj\Docs` para futuros proyectos del ecosistema.
