# Tareas: Separación de arquitectura Flet y Core

## Tareas

- [x] **T01 — Configuración y dependencias**: Configurar `pyproject.toml` para incluir `flet[desktop]==0.86.5` como dependencia unificada y preparar `src-flet` en el empaquetado.
- [x] **T02 — Traslado de la UI a `src-flet/`**: Mover las vistas, componentes, diálogos y aplicación de `src/davinci_flow/ui/desktop/` a `src-flet/` bajo Screaming Architecture (`app/`, `features/`, `shared/`).
- [x] **T03 — Punto de entrada `src-flet/main.py`**: Crear el entrypoint directo para Flet y conectar la invocación directa a `davinci_flow`.
- [x] **T04 — Consolidación de entornos y scripts**: Eliminar `.venv-pypy` y `.venv-resolve`, actualizar `scripts/start-desktop.ps1` y `scripts/setup-desktop.ps1` para usar `uv` y un único `.venv`.
- [x] **T05 — Integración con lanzador de Resolve**: Actualizar `installer.py` y `desktop_launcher.py` para invocar la UI de forma directa sin intermediarios de subproceso complejos.
- [x] **T06 — Limpieza de residuos**: Purgar `src/davinci_flow.egg-info/` y verificar `.gitignore`.
- [x] **T07 — Pruebas unitarias**: Adaptar `tests/test_desktop.py` a la nueva estructura y verificar que todos los tests (180/180) pasen al 100%.
- [x] **T08 — Documentación Core**: Documentar el estándar de estructura para proyectos Python en `D:\Proyectos\biglexj\Docs\stacks\python\python-baseline.md`.
