# Validación: Separación de arquitectura Flet y Core

## Criterios de Validación

- [x] V1: `pyproject.toml` define `flet[desktop]==0.86.5` y `uv sync` sincroniza el entorno `.venv` único sin errores.
- [x] V2: `.venv-pypy` y `.venv-resolve` eliminados. Solo existe `.venv` en la raíz.
- [x] V3: `src/davinci_flow.egg-info` eliminado.
- [x] V4: `src-flet/` contiene la UI completa (`main.py`, `app/`, `features/`, `shared/`) bajo Screaming Architecture.
- [x] V5: `tests/` pasa al 100% (180 pruebas en verde en 1.85s).
- [x] V6: Invocación directa y scripts (`scripts/start-desktop.ps1`, `scripts/setup-desktop.ps1`) alineados con CPython 3.13.
- [x] V7: Documentación de estándar de arquitectura Python agregada en `D:\Proyectos\biglexj\Docs\stacks\python\python-baseline.md`.

## Evidencia

1. **Entorno unificado con `uv`**:
   - `uv sync --project . --python .\.venv\Scripts\python.exe` ejecutado con éxito instalando `davinci-flow==0.2.0` con `flet[desktop]==0.86.5`.
   - `.venv-pypy` y `.venv-resolve` purgados con `Remove-Item -Recurse -Force`.
   - Único `.venv` verificado mediante `Get-ChildItem -Directory -Force .venv*`.

2. **Screaming Architecture en `src-flet/`**:
   - `src-flet/app/` (shell, `app.py`, `instance.py`, `runtime.py`).
   - `src-flet/features/` (`editor/`, `catalog/`, `library/`, `settings/`).
   - `src-flet/shared/` (`components.py`, `path_picker.py`).
   - `src-flet/main.py` como punto de entrada directo.
   - Purgada la carpeta obsoleta `src/davinci_flow/ui/desktop`.

3. **Pruebas unitarias**:
   - `.\.venv\Scripts\python.exe -m unittest discover tests`
   - Resultado: **Ran 180 tests in 1.855s - OK**.
   - `test_desktop.py`: **Ran 20 tests in 0.998s - OK**.

4. **Documentación Core**:
   - Redactado `D:\Proyectos\biglexj\Docs\stacks\python\python-baseline.md` cubriendo la Screaming Architecture, el patrón de dos raíces estilo Tauri (`src/` backend vs `src-flet/` frontend), el entorno unificado con `uv` y las normas de espacio de nombres.
