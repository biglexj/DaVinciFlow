# Auto-Updater y Panel de Actualizaciones en Ajustes — Validación

- Proceso: `2026-09-08_auto-updater-ajustes`
- Fecha: `2026-09-08`

## Resumen de Verificaciones

| Caso / Prueba | Método | Resultado Esperado | Resultado Real |
|---|---|---|---|
| Activación en Core Profile | Inspección de `core_profile.md` | Autoactualización figura como activa y enlazada con Docs Core | ✅ Aprobado (`core_profile.md` actualizado) |
| Parseo de Release GitHub | `test_updater.py` | Extracción correcta de versión, URLs, asset instalador y notas | ✅ Aprobado (`test_parse_release_success`, `test_parse_release_empty_tag`) |
| Comparación Semántica | `test_updater.py` | `0.3.0` < `0.3.1`, `1.0.0` > `0.9.9`, igualdad no es mayor | ✅ Aprobado (`test_is_newer_version`) |
| Sanitización Canónica Markdown | `test_updater.py` | Eliminación de `#`, `**`, `*`, viñetas a `• `, rutas locales purgadas | ✅ Aprobado (`test_sanitize_release_notes_markdown`, `test_sanitize_removes_local_paths`) |
| Manejo Resiliente Red | `test_updater.py` | Errores de API (HTTP 404, 403 rate-limit, URLError) devuelven `None` silenciosamente | ✅ Aprobado (`test_check_github_release_network_error`) |
| Toast Flotante Superior (4s) | `test_desktop.py` | Toast centrado arriba en `page.overlay` con auto-desvanecimiento | ✅ Aprobado (`test_show_toast_overlay`) |
| Panel Ajustes en Columna Derecha | Render en `SettingsView` | Distribución en dos columnas simétricas (`expand=1`), sin envoltura forzada y ancho dinámico | ✅ Aprobado (`test_settings_updater_panel_layout_and_interactions`) |
| Comprobación desde Acerca de | Invocación en `about_dialog.py` | Cierre síncrono inmediato del modal (`dialog.open = False`, `dialog.update()`) antes de consultar versión | ✅ Aprobado (`test_about_dialog_presentation_and_channels`) |
| Suite completa de tests | `unittest discover -s tests` | 100% pruebas pasando sin regresiones | ✅ Aprobado (199/199 pruebas en 4.760s) |

## Evidencia

```
Ran 199 tests in 4.760s

OK
[SIMULACIÓN (Dry-Run)] Ejecución: exec_1
Proyecto: Proj | Línea de tiempo: TL
Total elementos planificados: 0 (Estado: completed)
Proyecto: TestProj
Línea de tiempo: TestTimeline
Pista de subtítulos: 1
Tema: ely | Perfil: natural
Huella origen (SHA-256): abcd1234efgh5678…
Total bloques: 1 (Capas: {1: 0, 2: 1, 3: 0})
  [0-24] (2 capas / statement) [C: Contexto] [M: Prueba]
Proyecto: TestProj
Línea de tiempo: TestTimeline
Pista de subtítulos: 1
Tema: ely | Perfil: natural
Huella origen (SHA-256): abcd1234efgh5678…
Total bloques: 1 (Capas: {1: 1, 2: 0, 3: 0})
  [0-24] (1 capas / statement) [M: Prueba]
Comparando contra plan previo: plan_old
✅ Idempotencia: Los subtítulos son 100% idénticos. No se requieren cambios.
```
