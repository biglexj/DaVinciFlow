# Flujo de revisión y selector de rutas — Validación

- Estado: `COMPLETED`

## Comprobaciones

- [x] V01 — Agente — Comprobar que `Proposal.approve_all()` marca todas las decisiones válidas como `reviewed=True` y rechaza estados corruptos. (Verificado en `test_approve_all_marks_all_decisions_reviewed_and_validates`).
- [x] V02 — Agente — Comprobar que `close_review()` en `EditorView` oculta la tarjeta y limpia la selección de fila, y pulsar la fila activa de nuevo la cierra. (Verificado en `test_editor_review_card_close_and_toggle`).
- [x] V03 — Agente — Comprobar que `apply()` en `EditorView` ofrece aprobar y aplicar si hay bloques pendientes sin lanzar error. (Verificado en `test_editor_apply_prompts_bulk_approval_when_unreviewed` y `test_editor_approve_all_and_apply_flow`).
- [x] V04 — Agente — Comprobar que `get_system_drives()` en Windows retorna las unidades lógicas disponibles (C:\, D:\, etc.). (Verificado en `test_path_picker_drives_and_new_folder`).
- [x] V05 — Agente — Comprobar que el selector de archivos permite cambiar de disco y crear carpetas nuevas interactivamente. (Verificado en `test_path_picker_drives_and_new_folder`).
- [x] V06 — Agente — Suite completa de pruebas automatizadas ejecutada y superada al 100% (223/223 pruebas superadas).

## Registro de fallos

- Sin fallos registrados.

Al aprobar una comprobación, cambia `[ ]` por `[x]`. Si falla, mantenla pendiente y añade una sola línea con el motivo y la tarea relacionada.
