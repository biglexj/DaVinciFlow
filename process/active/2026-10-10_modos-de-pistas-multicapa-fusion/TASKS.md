# 2026-10-10_modos-de-pistas-multicapa-fusion — Tareas

- Estado: `IN_PROGRESS`

## Tareas

- [x] T01 — Incorporar `track_mode` (`"single"`, `"dual"`, `"triple"`) en `EditorialOptions` y contrato en `src/davinci_flow/editorial/model.py`.
- [x] T02 — Actualizar `ResolveTrackManager` (`src/davinci_flow/resolve/track_manager.py`) para admitir recuento de pistas dinámico (1, 2 o 3 pistas de texto) según el modo activo.
- [x] T03 — Refactorizar `EditorialWriter` (`src/davinci_flow/editorial/writer.py`) para proyectar las capas (`context`, `main`, `accent`) según el modo de pista seleccionado (`single`, `dual`, `triple`) sin forzar pistas no deseadas.
- [x] T04 — Integrar el selector de `Modo de Pistas` en la interfaz Flet (`editor_view.py`).
- [x] T05 — Crear pruebas unitarias completas en `tests/test_track_modes.py` para validar modos de 1, 2 y 3 pistas y regresión de `EditorialWriter`.
- [x] T06 — Ejecución completa de la suite de pruebas `unittest` y registro de evidencia en `VALIDATION.md`.

