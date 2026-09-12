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
- [x] Actualización de pruebas unitarias para 12 plantillas categorizadas en 4 packs (`basic`, `shorts`, `youtube`, `news`).

### 4. Resolución de Conflictos, Limpieza Atómica y Packs de Plantillas
- [x] Distinción de clips propios vs. ajenos en `writer.py`:
  - Los clips con prefijo `DF__` se identifican como artefactos de ejecuciones previas de DaVinci Flow y se omiten durante la comprobación de colisión foránea.
  - Comprobado en `tests/test_editorial_writer.py` (`test_df_prefixed_clips_are_treated_as_reversion_target_not_foreign_conflict`).
- [x] Excepción estructurada `EditorialConflictError`:
  - Reporta tupla de `EditorialConflictDetail` con pista, índice de pista, nombre de clip, fotogramas iniciales/finales, índice de subtítulo y texto.
  - Comprobado en `tests/test_editorial_writer.py` (`test_foreign_clip_in_destination_is_not_overwritten`).
- [x] Limpieza atómica de pistas DF (`clean_tracks` / `clean_df_tracks`):
  - Operación directa en Resolve que localiza y elimina clips situados en `DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT` y `DF_SFX` sin tocar pistas de usuario.
  - Validado en vivo en DaVinci Resolve Studio: 59 clips huérfanos eliminados limpiamente (`{'deleted_count': 59}` y posterior verificación `{'deleted_count': 0}`).
  - Comprobado en `tests/test_subtitles_view.py` (`test_clean_df_tracks_invokes_bridge`).
- [x] Mesa de revisión visual de conflictos en `EditorView`:
  - Filas colisionantes resaltadas con fondo oscuro rojizo (`#3B1818`), tipografía en rojo (`#EF4444`) e icono `⚠️`.
  - Tooltips detallados indicando el clip ajeno y el rango de fotogramas en conflicto.
  - Diálogo modal con explicación clara y botón de 1 clic «Limpiar pistas DF y reintentar».
  - Botón accesible `[Limpiar pistas DF]` en la barra de acciones de la mesa de edición.
- [x] Presets de estilos profesionales (.setting) categorizados:
  - `📱 Shorts Bold Pop` (`Shorts Bold - Contexto.setting`, `Shorts Bold - Principal.setting`, `Shorts Bold - Énfasis.setting`): calibrados para 9:16 vertical, trazo negro de 0.02, sombra paralela y resalte amarillo fluorescente `#FFEA00`.
  - `🎬 YouTube Dinámico` (`YouTube Dinámico - Contexto.setting`, `YouTube Dinámico - Principal.setting`, `YouTube Dinámico - Énfasis.setting`): interlineado elegante, resalte dorado `#FFBC00` y composición horizontal 16:9.
  - `📰 Noticiero TV` (`Noticiero TV - Contexto.setting`, `Noticiero TV - Principal.setting`, `Noticiero TV - Énfasis.setting`): estilo rótulo broadcast con alto contraste.
  - `✏️ Text+ Básico`: plantillas estándar minimalistas.
- [x] Catálogo con filtro de categorías y aplicación de packs en 1 clic:
  - Menú desplegable de categorías en `CatalogView` (`Todos`, `📱 Shorts / TikTok`, `🎬 YouTube Dinámico`, `📰 Noticiero / TV`, `📁 Media Pool / Proyecto`, `🎨 Text+ Básico`).
  - Tarjeta de accesos rápidos con botones de 1 clic para asignar las 3 capas (`context`, `main`, `accent`) simultáneamente.
  - Método `choose_pack()` en `EditorialController` validado en `tests/test_subtitles_view.py` (`test_choose_pack_selects_matching_templates`).
- [x] Suite completa de pruebas ejecutada: 251 pruebas ejecutadas en 6.549s, 100% en verde (`OK`).


