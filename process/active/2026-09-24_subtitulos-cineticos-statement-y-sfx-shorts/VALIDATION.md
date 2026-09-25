# 2026-09-24_subtitulos-cineticos-statement-y-sfx-shorts — Validación

- Estado: `IN_PROGRESS`
- Fecha: `2026-09-24`

## Evidencia Técnica

### 1. Auditoría de Línea de Tiempo Real (Resolve 21.1)
- **Proyecto Horizontal (`La Falta de Comunicación`)**:
  - `1920x1080` @ 24fps, duración 10.74 min.
  - Subtítulos nativos en `S1` (587 clips, promedio 0.96s / 3.1 palabras).
  - B-Roll Anime en `V1` (132 clips, corte medio 4.88s).
  - Inserts Ely en `V2` (11 clips).
  - SFX en `A5` (28 transiciones) y `A6` (26 pops).
- **Proyecto Vertical (`Shorts / Timeline 1`)**:
  - `1080x1920` @ 24fps, duración 2.27 min.
  - Disposición en 3 tercios: Video de fondo en `V1`/`V2`, subtítulo central dinámico en `V3`, personaje Ely en `V4`.
  - Correlación V4 (expresiones) vs A4 (SFX): Desfase 0 a -3 frames en entradas visuales (`pop_02.mp3`, `suction_pop_07.mp3`, `swoosh_02.mp3`).
  - Título cinético identificado: `Statement` (`Fusion Title - Statement`), empaquetado en `Templates.drfx` (`Edit/Titles/Subtitles/Animated/Statement.setting`).
  - Bin nativo descubierto: `SC-87-Impact Statement.drb` importable con `ImportFolderFromFile` hacia `MediaPool`, generando un clip de tipo `Título – Fusion` compatible con `AppendToTimeline` para cualquier pista de video.

### 2. Pruebas Automatizadas
- **Suite completa de pruebas unitarias**: 269 pruebas ejecutadas y aprobadas al 100% en 6.3 segundos (`python -m unittest discover tests`).
  - `tests.test_kinetic_titles`: Verificación de catálogo (`statement`, `word_highlight`, `rotate`, `lollipop`, `slide_in`), cálculo matemático de timecode (`frames_to_timecode_string`), inserción dirigida con aislamiento de pistas (`SetTrackLock`), y mutación de `StyledText`.
  - `tests.test_sfx_expression_sync`: Detección precisa de cortes de expresión en `V4`, debounce de cortes consecutivos (< 8 frames), alternancia de pops (`pop_02` / `suction_pop_07`), detección de swoosh para entradas, y anticipación exacta de -3 a -5 fotogramas en `A4`.
  - `tests.test_timeline_writer`: Integración nativa de `KineticTitleWriter` en `_insert_fusion_title` sin generación de archivos carrier `.avi`.
  - `tests.test_main_cli`: Verificación de flags CLI `--preset` y comando de sincronización de audio `--sync-sfx`.

### 3. Comprobación de Límites de Código
- `src/davinci_flow/resolve/kinetic_titles.py`: 518 líneas (límite < 900).
- `src/davinci_flow/sfx/expression_sync.py`: 316 líneas (límite < 900).
- `src/davinci_flow/resolve/timeline_writer.py`: 810 líneas (límite < 900).
- `src/davinci_flow/application.py`: 557 líneas (límite < 900).
- `src/davinci_flow/__main__.py`: 391 líneas (límite < 900).

### 4. Validación en Vivo con Biglex (Proyecto `¿POR QUÉ TERMINAR UNA HISTORIA NOS DEJA VACÍOS`)
- **Evidencia Empírica de Timeout en ResolveMCP**:
  - Al procesar 120 subtítulos dinámicos multicapa (con Fusion Titles y SFX), la ejecución se detenía exactamente en `00:02:05:20` (~subtítulo 38) con error: `Resolve: Script timed out after 60s. Avoid long iterations; fetch only what you need.`
  - Causa raíz demostrada científicamente: `ResolveMCP.exe` de Blackmagic impone un hard cap estricto de 60.0 segundos por script (`max: 60` en `run_script_unsafe`).
  - Solución elegante implementada: En `resolve_bridge.py`, las operaciones masivas de escritura (`apply`, `undo`, `clean_tracks`) se enrutan de forma inteligente y transparente vía CPython 3.13 nativo (`timeout = None`), permitiendo escrituras de secuencias completas sin ninguna interrupción.

### 5. Rediseño de Interfaz y Modularidad
- **Editor UI**: `Dirección creativa` compactada horizontalmente e integrada en la misma fila con `Proponer con IA`, `Abrir propuesta`, `Guardar` y `Aprobar todo`. Los controles de aplicación y conteo se alinean armoniosamente en la sub-barra.
- **Plantillas (CatalogView)**: Eliminación del `ListView` anidado causante del doble scrollbar. Cada plantilla ahora cuenta con tarjeta interactiva con previsualización visual de tipografía (`Montserrat`, `TextPlus`), colores (`Énfasis` en ámbar `#FFBC00`, `Principal` en blanco bold, `Contexto` en azul grisáceo) y badges de rol y categoría.
- **Navegación Modular**: Barra lateral expandida con áreas dedicadas:
  1. `Asistente IA` (brainstorming narrativo y transferencia directa de directrices creativas).
  2. `Editor` (mesa de trabajo, subtítulos y revisión).
  3. `Efectos (SFX)` (catálogo sonoro, ganancia, anticipación y pistas).
  4. `B-Rolls` (clips e imágenes de apoyo indexados).
  5. `Plantillas` (catálogo y estilos).
  6. `Biblioteca` (administración de carpetas).
  7. `Corrección` (revisión ortográfica y decouple de subtítulos crudos).
  8. `Ajustes` (modelos IA, tokens, auto-updater).

### 6. Batería de Pruebas Automatizadas
- **Total ejecutadas**: 278 pruebas unitarias aprobadas al 100% (0 fallos, 0 errores en 10.2s).
- **Límites de archivo respetados**: Ningún archivo excede las 900 líneas.

