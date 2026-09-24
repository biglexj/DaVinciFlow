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
- [ ] Ejecución de suite completa de pruebas unitarias (`python -m unittest discover tests`).

### 3. Pruebas de Integración en DaVinci Resolve
- [ ] Inserción de `Statement` en pista `V3` con asignación de `StyledText`.
- [ ] Sincronización de SFX en pista `A4`.
