# Auto-Updater y Panel de Actualizaciones en Ajustes — Plan

- Estado: `IN_PROGRESS`
- Fecha: `2026-09-08`
- Proyecto: `DaVinci Flow`
- Autor: `biglexj`

## Objetivo

Implementar el sistema de auto-actualización desde GitHub Releases para DaVinci Flow conforme al estándar de la Documentación Core (`UpdateChecker`, sanitización de notas Markdown, verificación silenciosa al iniciar y manual con Toast flotante de 4 segundos), e integrar el panel detallado de actualizaciones en la vista de Ajustes en el espacio horizontal disponible a la derecha, además de los scripts y protocolos de lanzamiento oficiales.

## Alcance

- Incluye:
  - Activación de la capacidad de auto-actualización en `.agents/rules/core_profile.md`.
  - Módulo central `UpdateChecker` y modelo `UpdateRelease` en `src/davinci_flow/updater/` (parseo de GitHub Releases API, comparación semántica de versiones `is_newer_version`, y sanitización canónica `sanitize_release_notes`).
  - Rediseño de la vista `SettingsView` en [settings_view.py](file:///d:/Proyectos/biglexj/DaVinciFlow/src-flet/features/settings/settings_view.py) distribuyendo el contenido en columnas:
    - Columna izquierda: Modelos IA & Credenciales + Acerca de DaVinci Flow.
    - Columna derecha (espacio señalado por el usuario): Panel completo de **Actualizaciones de DaVinci Flow** con estado actual, canal oficial de GitHub Releases, botón «Buscar actualizaciones», indicador de carga, visualización de notas de versión sanitizadas y botones de acción («Descargar actualización», «Ver en GitHub», «Historial de versiones»).
  - Verificación silenciosa en segundo plano al iniciar la app sin interrupción si está al día.
  - Verificación manual con notificación flotante (Toast flotante centrado superior durante 4 segundos cuando se esté en la última versión: `✅ Estás en la última versión`).
  - Integración del botón de búsqueda de actualizaciones en el modal `AboutDialog` con cierre previo y transición síncrona.
  - Script oficial de publicación de releases `scripts/release/build-release.ps1` y utilitarios `scripts/release/ReleaseTools.ps1` adaptados para DaVinci Flow siguiendo `Docs/features/auto-updater/release_script_guide.md`.
  - Pruebas unitarias completas de `UpdateChecker`, sanitización, layout de ajustes y flujo de verificación.
- No incluye:
  - Instalador silencioso con elevación UAC en segundo plano (las versiones de DaVinci Flow se distribuyen como código/paquete y repositorio de GitHub Releases).

## Enfoque

1. Actualizar `.agents/rules/core_profile.md` para declarar activa la función de autoactualización y asociar los documentos Core pertinentes.
2. Implementar `src/davinci_flow/updater/checker.py` con `UpdateRelease`, `UpdateChecker`, `is_newer_version`, `sanitize_release_notes` y `check_github_release`.
3. Implementar componente Toast flotante y métodos de verificación en `DesktopApp` (`src-flet/app/app.py`).
4. Reestructurar `SettingsView` en `src-flet/features/settings/settings_view.py` a dos columnas con el panel de actualizaciones a la derecha.
5. Conectar el botón de búsqueda de actualizaciones en `AboutDialog` (`src-flet/features/about/about_dialog.py`).
6. Crear `scripts/release/ReleaseTools.ps1` y `scripts/release/build-release.ps1`.
7. Escribir tests en `tests/test_updater.py` y actualizar `tests/test_desktop.py`.
8. Ejecutar validaciones y documentar evidencia.

## Criterios de finalización

- [ ] `core_profile.md` actualizado con autoactualización activa.
- [ ] Panel de actualizaciones visible a la derecha de Ajustes en el espacio libre.
- [ ] `UpdateChecker` parsea correctamente releases de GitHub y sanitiza Markdown.
- [ ] Toast flotante centrado superior de 4 segundos al verificar manualmente sin novedades.
- [ ] Diálogo «Acerca de» sincronizado para comprobar actualizaciones.
- [ ] Suite de pruebas al 100% en verde.
