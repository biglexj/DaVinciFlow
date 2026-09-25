# 2026-09-24_subtitulos-cineticos-statement-y-sfx-shorts — Tareas

- Estado: `IN_PROGRESS`

## Ejecución

- [x] T01 — Mapeo y extracción de la plantilla `Statement` y catálogo de subtítulos cinéticos para DaVinci Flow.
- [x] T02 — Implementación de inserción nativa con `InsertFusionTitleIntoTimeline` y `AppendToTimeline` en pista de video dedicada (`V3`) con duración exacta.
- [x] T03 — Inyección dinámica de `StyledText` y atributos de estilo en el nodo `Template`/TextPlus del Fusion Title en tiempo real.
- [x] T04 — Implementación del motor de auto-emparejamiento de expresiones visuales (`V4`) con SFX en `A4` (`pop`, `swoosh`, `suction_pop`) con anticipación de -3 fotogramas.
- [x] T05 — Eliminación definitiva de intermediarios pre-renderizados (`.mov` y carriers `.avi`) en el flujo de subtítulos y títulos nativos.
- [x] T07 — Validación interactiva en vivo con Biglex en DaVinci Resolve en su proyecto real (120 subtítulos, detección del límite de 60s en ResolveMCP).
- [x] T08 — Resolución del timeout de 60s en `resolve_bridge.py` y `mcp_bridge.py`: derivar operaciones de escritura masiva (`apply`, `undo`, `clean_tracks`) a CPython 3.13 nativo sin límite de tiempo en modo `auto`.
- [x] T09 — Reorganización visual del Editor (`editor_view.py`): alinear `Dirección creativa` compacta y horizontalmente con `Proponer con IA`, `Abrir propuesta`, `Guardar` y `Aprobar todo`.
- [x] T10 — Corrección del scrollbar doble en `Plantillas` (`catalog_view.py`) y adición de vista previa visual de tipografía, estilos y roles por tarjeta.
- [x] T11 — Refactorización modular de navegación en barra lateral (`app.py`): vistas dedicadas para `Asistente IA`, `Editor`, `Efectos de sonido (SFX)`, `B-Rolls`, `Plantillas`, `Biblioteca` y `Ajustes`.
- [x] T12 — Pruebas unitarias de regresión y verificación completa en `tests/` (278 pruebas pasando, 0 fallos).
- [x] T13 — Motor de montaje e inserción nativa de B-Rolls (`broll_writer.py` y `test_broll_writer.py`): encadenamiento dinámico zero-gaps, aislamiento de audio (`mediaType: 1`), compensación de ratio FPS fuente-timeline, y segmentación de seguridad Content ID (< 8s).

Las pruebas y evidencia empírica se documentan en `VALIDATION.md`.
