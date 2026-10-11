# 2026-10-10_modos-de-pistas-multicapa-fusion — Plan

- Estado: `IN_PROGRESS`
- Fecha: `2026-10-10`
- Proyecto: `DaVinci Flow`
- Solicitante: `biglexj`

## Objetivo

Implementar la asignación dinámica y configurable de pistas de video (1, 2 o 3 pistas según el modo editorial seleccionado) para títulos y subtítulos nativos Fusion Text+, superando la limitación de pista única rígida de SnapCaptions y permitiendo al editor enrutar libremente a pistas dedicadas (`DF_*`) o pistas existentes del proyecto.

## Alcance

- Incluye:
  - **Soporte de tres modos de maquetación de pistas en el contrato editorial**:
    - `single` (1 pista): Toda la locución/subtítulos se consolidan en una sola fila (ej. `DF_MAIN` o pista base seleccionada).
    - `dual` (2 pistas): Capa base (`DF_MAIN`) + Capa de Énfasis / Highlight (`DF_ACCENT`).
    - `triple` (3 pistas): Capa Contexto (`DF_CONTEXT`) + Capa Principal (`DF_MAIN`) + Capa Énfasis (`DF_ACCENT`).
  - **Flexibilidad en `ResolveTrackManager` y `EditorialWriter`**:
    - Creación y verificación exclusiva de las pistas requeridas por el modo activo (no forzar siempre 3 pistas de texto si el usuario eligió modo simple o dual).
    - Soporte de enrutamiento a pistas de video preexistentes (`target_tracks`) sin forzar que estén por encima de todo cuando el editor decida trabajar dentro de su estructura de montaje.
  - **Parametrización en `EditorialOptions` y `GenerationPlan`**:
    - Campo `track_mode` (`single`, `dual`, `triple`) con validación estricta y valor por defecto configurable (`triple` para riqueza editorial completa o `dual`/`single` según preferencia).
  - **Selector visual en la interfaz de DaVinci Flow (`editor_view.py` / `settings_view.py`)**:
    - Selector interactivo de Modo de Pistas (1 Pista · Simple, 2 Pistas · Base + Énfasis, 3 Pistas · Triple Capa).
  - **Pruebas unitarias completas en `tests/`** verificando la creación exacta de pistas y asignación en cada modo.
- No incluye:
  - Eliminación de la jerarquía semántica del asistente IA (Gemini sigue clasificando contexto, principal y énfasis; el mapeador adapta cómo se proyectan en las pistas).

## Criterios de finalización

- [ ] Campo `track_mode` agregado a `EditorialOptions` con validación (`"single"`, `"dual"`, `"triple"`).
- [ ] `ResolveTrackManager` ajustado para crear solo las pistas de video necesarias según el modo activo.
- [ ] `EditorialWriter` y `ResolveTimelineWriter` mapean las capas (`context`, `main`, `accent`) a las pistas correctas según el modo:
  - En `single`: Todo el texto activo se asigna a la pista única.
  - En `dual`: `context` y `main` se combinan en la pista base, y `accent` va a la pista de énfasis.
  - En `triple`: Asignación individual a las 3 pistas dedicadas.
- [ ] Selector interactivo de Modo de Pistas en la interfaz gráfica.
- [ ] Pruebas unitarias nuevas y existentes superadas al 100% con `unittest`.
- [ ] Documentación de evidencia en `VALIDATION.md` y registro en `APPROVAL.md`.
