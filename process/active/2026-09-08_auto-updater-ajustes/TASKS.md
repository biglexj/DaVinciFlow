# Auto-Updater y Panel de Actualizaciones en Ajustes — Tareas

- Proceso: `2026-09-08_auto-updater-ajustes`

## Tareas

- [x] 1. Sincronizar `.agents/rules/core_profile.md` (activar función de auto-actualización y enlazar `features/auto-updater/auto_updater.md` y `features/auto-updater/desktop-update-flow.md`).
- [x] 2. Implementar `src/davinci_flow/updater/checker.py` (`UpdateRelease`, `UpdateChecker`, `is_newer_version`, `sanitize_release_notes`, `check_github_release`).
- [x] 3. Implementar Toast flotante centrado superior (4s) y lógica de comprobación en `DesktopApp` (`src-flet/app/app.py`).
- [x] 4. Reestructurar `SettingsView` ([settings_view.py](file:///d:/Proyectos/biglexj/DaVinciFlow/src-flet/features/settings/settings_view.py)) con disposición a dos columnas e incorporar la tarjeta completa de Actualizaciones a la derecha.
- [x] 5. Conectar comprobación de actualizaciones en `AboutDialog` ([about_dialog.py](file:///d:/Proyectos/biglexj/DaVinciFlow/src-flet/features/about/about_dialog.py)).
- [x] 6. Crear `scripts/release/ReleaseTools.ps1` y `scripts/release/build-release.ps1` para lanzamientos oficiales de DaVinci Flow.
- [x] 7. Escribir pruebas unitarias en `tests/test_updater.py` y ampliar `tests/test_desktop.py`.
- [x] 8. Ejecutar suite de pruebas completa y registrar evidencia en `VALIDATION.md` y `APPROVAL.md`.
