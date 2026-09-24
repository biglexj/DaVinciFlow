# 2026-09-24_subtitulos-cineticos-statement-y-sfx-shorts — Tareas

- Estado: `IN_PROGRESS`

## Ejecución

- [x] T01 — Mapeo y extracción de la plantilla `Statement` y catálogo de subtítulos cinéticos para DaVinci Flow.
- [x] T02 — Implementación de inserción nativa con `InsertFusionTitleIntoTimeline` y `AppendToTimeline` en pista de video dedicada (`V3`) con duración exacta.
- [x] T03 — Inyección dinámica de `StyledText` y atributos de estilo en el nodo `Template`/TextPlus del Fusion Title en tiempo real.
- [x] T04 — Implementación del motor de auto-emparejamiento de expresiones visuales (`V4`) con SFX en `A4` (`pop`, `swoosh`, `suction_pop`) con anticipación de -3 fotogramas.
- [x] T05 — Eliminación definitiva de intermediarios pre-renderizados (`.mov` y carriers `.avi`) en el flujo de subtítulos y títulos nativos.
- [x] T06 — Pruebas unitarias de cobertura completas para nuevos componentes en `tests/` (269 pruebas pasando, 0 fallos).
- [ ] T07 — Validación interactiva en vivo con Biglex en DaVinci Resolve tras concluir su sesión de grabación de video.

Las pruebas y evidencia empírica se documentan en `VALIDATION.md`.
