# Desacople de Fase de Crudo y Pestaña Dedicada «Corrección de Subtítulos» — Validación

- Proceso: `process/active/2026-09-11_correccion-subtitulos-y-desacople-crudo/`
- Estado: `VERIFIED`

## Evidencias de Comprobación

### 1. Pruebas Automatizadas
- [x] Ejecución de suite completa con `uv run python -m unittest discover -s tests`:
  - **Resultado**: 243 pruebas ejecutadas en 5.483s, 100% en verde (`OK`).
  - Cero errores, cero fallos.
- [x] Pruebas unitarias de `SubtitlesView` en `tests/test_subtitles_view.py`:
  - Búsqueda y reemplazo global con conteo de sustituciones y subtítulos modificados (`test_find_and_replace`).
  - Normalización ortográfica determinista en español (`test_normalize_all_subtitles`).
  - Glosario de términos (`test_apply_glossary`).
  - Edición rápida de bloque individual (`test_choose_cue_and_edit_manually`).
  - Sincronización hacia `EditorialController` (`test_sync_to_editor`).
  - Regresión de seguridad de layout Flutter (`test_subtitles_view_layout_safety`): verifica que ningún `ft.Row(wrap=True)` contenga hijos con `expand=True`, previniendo la pantalla/caja gris de error (`ErrorWidget`).
- [x] Pruebas de captura con elementos sintéticos/generadores en `tests/test_mcp_bridge.py`:
  - `test_generator_has_no_offsets_but_captured_in_fingerprint`: valida que generadores (tipo `generator`, como "Color sólido") sin offsets de media pool no lancen excepción y se incorporen limpiamente a la huella de montaje.
  - `test_missing_offsets_on_media_fail_closed`: valida que clips de vídeo reales con offsets ausentes o corruptos sigan fallando en modo cerrado.
- [x] Pruebas de auto-reconciliación y resiliencia de lotes LLM en `tests/test_editorial.py`:
  - `test_batch_omission_reconciles_on_second_attempt_highlights`: valida que si la LLM omite un subtítulo en un lote (ej. corte de 1 cuadro) en ambos intentos en modo highlights, el subtítulo omitido se reconcilia como desactivado (`enabled=False`, sin rótulo) mientras que todas las propuestas activas de la LLM se conservan intactas.
  - `test_batch_omission_reconciles_on_second_attempt_captions`: valida que si la LLM omite un subtítulo en modo captions, se reconcilia de forma segura con el texto original y la plantilla por defecto.
  - Ejecución de suite completa: 245 pruebas ejecutadas en 6.863s, 100% en verde (`OK`).
- [x] Pruebas de desacople de crudo y fases en `tests/test_subtitles_view.py`:
  - Reconocimiento de montaje avanzado con cortes y subtítulos en `source_summary` (`test_stage_labels_and_montage_recognition`).
  - Navegación interactiva de etapas sin requerir llamada a IA (`test_interactive_stage_navigation`).
  - Desbloqueo de revisión directa 1:1 al hacer clic en un bloque de subtítulo (`test_direct_review_unlock_on_cue_selection`).
  - Métodos `create_default_proposal` y `update_cues` en `EditorialController` validados (`ControllerDirectProposalTests`).

### 3. Comprobación de Calibración Vertical, Plantillas Media Pool y Multi-Carpeta
- [x] Calibración vertical de títulos Fusion en tercio inferior seguro:
  - Formato vertical (9:16 Shorts/Reels/TikTok): Y calibrado dinámicamente en rango `0.285 - 0.355` con separación compacta de `0.035`, situando el texto bajo el pecho/rostro y fuera de la zona de controles inferiores.
  - Validación de posiciones por roles activos comprobada en `tests/test_editorial.py` (`test_calculate_layer_y_vertical_and_horizontal`).
  - Actualización de posiciones predeterminadas en archivos `.setting` de `basic_titles` (`Contexto: 0.24`, `Principal: 0.19`, `Énfasis: 0.14`).
- [x] Indexación ampliada de presets en el Media Pool (`template_scanner.py`):
  - Detección de títulos y composiciones Fusion tanto en carpetas `DaVinciFlow` como en carpetas de títulos (`Titles`, `Subtitles`, `Plantillas`) y directamente en la raíz `Master`.
  - Exclusión garantizada de archivos de vídeo/audio/captura.
  - Comprobado en `tests/test_template_scanner.py` (`test_scan_discovers_titles_in_root_master_and_title_bins`).
- [x] Selección robusta de nodo TextPlus en composiciones complejas (`writer.py`):
  - Búsqueda recursiva dentro de macros y grupos (como la plantilla `Statement` de MrAlexTech).
  - Priorización de nodos nombrados `Template`, `StyledText`, `Main` o `Principal`, evitando errores de ambigüedad.
  - Comprobado en `tests/test_editorial.py` (`test_text_tool_prefers_named_template_when_multiple`).
- [x] Soporte multi-carpeta en la interfaz de Biblioteca (`LibraryView` y `library.py`):
  - Configuración de múltiples rutas por categoría separadas por `;`.
  - Tarjeta interactiva con listado visual de carpetas añadidas, botón para remover individualmente y botón `+ Añadir carpeta` mediante selector nativo.
  - Indexación unificada sin duplicados de recursos compartidos.
- [x] Suite completa de pruebas ejecutada: 248 pruebas ejecutadas en 6.011s, 100% en verde (`OK`).

