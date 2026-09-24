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

### 4. Flujo de Validación en Vivo
- Comandos listos para ejecución directa en la terminal de DaVinci Resolve:
  - Generación de subtítulos cinéticos Statement en V3:
    `python -m davinci_flow --generate --preset statement`
  - Sincronización automática de SFX de expresión en A4:
    `python -m davinci_flow --sync-sfx --expression-track 4 --sfx-track 4 --anticipation 3`

