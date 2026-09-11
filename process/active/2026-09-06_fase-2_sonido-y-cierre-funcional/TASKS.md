# Fase 2 — Dos pistas de sonido y cierre funcional — Tareas

- Estado: EN EJECUCIÓN ACTIVA (2026-09-10).
- Dependencia: Requiere fase 1 validada y aceptación de su muestra. Reutilizar su contrato editorial y sus plantillas compatibles.

## Ejecución

- [x] T01 — Auditar sfx/, track_manager.py, timeline_writer.py, generation/record.py y reconciler.py frente a los contratos de fase 1.
- [x] T02 — Catalogar SFX y extender el contrato para transiciones y énfasis con ganancia, fundidos y referencia al bloque (`DEFAULT_SFX_ASSETS` en `model.py`, `BUILTIN_SFX_IDS`).
- [x] T03 — Implementar decisiones sonoras LLM y validadores de densidad, repetición y tiempos (`EditorialPlanner` rítmico + auto-inyección en `resource_context`).
- [x] T04 — Implementar revisión y selección en la interfaz (`EditorView` con columna 'Sonido', selector de efectos, persistencia de `resource_id` e indicador de 3 etapas).
- [ ] T05 — Completar regeneración selectiva, manejo de fallos parciales y reversión por ejecución; conservar compatibilidad de registros.
- [ ] T06 — Corregir fallos encontrados en la muestra y posteriormente en un vídeo completo.
- [ ] T07 — Entregar evidencia audiovisual y límites conocidos; habilitar fase 3 solo después del cierre funcional.

Registrar pruebas en VALIDATION.md. Al relevar al agente, anotar aquí la tarea activa, archivos modificados y siguiente acción.

## Estado de la sesión (2026-09-10)

- Tarea activa: T05 / T06 (Verificación funcional e integración de pistas de audio en Resolve).
- Archivos modificados en la sesión:
  - `src/davinci_flow/editorial/model.py`: Inclusión de `BUILTIN_SFX_IDS`, mapeo de `resource_id` a `sfx_proposal` en `generation_plan()`.
  - `src/davinci_flow/editorial/controller.py`: Inyección automática de `DEFAULT_SFX_ASSETS` en `resource_context()`.
  - `src/davinci_flow/editorial/writer.py`: Aseguramiento automático de pista de audio `DF_SFX` y bypass de Fusion comps para items de audio.
  - `src/davinci_flow/editorial/planner.py`: Guía de dirección creativa sonora para el LLM.
  - `src-flet/features/editor/editor_view.py`: Header de 3 etapas (`1. Ingesta del Crudo` -> `2. Mesa de Revisión` -> `3. Aplicación en Resolve`), columna `Sonido`, selector en tarjeta de revisión, bindings y `form_changed` sync.
  - `tests/test_editorial.py`, `tests/test_desktop.py`: Pruebas automatizadas de cobertura para catálogo SFX e inyección de pistas (227 tests passing).
- Siguiente acción: Comprobación de aplicación real contra Resolve y validación de inserción de pistas combinadas (video + audio DF_SFX).

