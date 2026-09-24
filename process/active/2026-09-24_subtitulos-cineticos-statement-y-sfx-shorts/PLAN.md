# 2026-09-24_subtitulos-cineticos-statement-y-sfx-shorts — Plan

- Estado: `IN_PROGRESS`
- Fecha: `2026-09-24`
- Proyecto: `DaVinci Flow`
- Solicitante: `biglexj`

## Objetivo

Implementar un motor utilitario en DaVinci Flow para generación de subtítulos cinéticos nativos (plantilla `Statement` y animadas en `V3`) y emparejamiento automático de efectos de sonido (SFX en `A4`) con cambios visuales de expresiones de personaje (`V4`), eliminando totalmente archivos pre-renderizados (`.mov` / carriers `.avi`) y garantizando edición nativa en el Inspector de Resolve.

## Alcance

- Incluye:
  - Generador de subtítulos dinámicos basados en plantillas de Fusion Title nativas (`Statement`, `Word Highlight`, `Lollipop`, etc.) insertables en pista de video dedicada (`V3`) con `StyledText` editable.
  - Soporte de importación de presets de títulos nativos vía bins `.drb` / plantillas del sistema para permitir colocación con `AppendToTimeline` en cualquier pista destino (`trackIndex`) y fotograma exacto (`recordFrame`), o mediante `InsertFusionTitleIntoTimeline`.
  - Módulo de sincronización automática de audio SFX (`pop_02.mp3`, `suction_pop_07.mp3`, `swoosh_02.mp3`) en la pista de audio `A4` emparejado con cada fotograma de entrada de expresión visual en `V4`.
  - Adaptación explícita para proyectos Verticales (9:16 Shorts) con visor en 3 tercios vs. Horizontales (16:9).
  - Pruebas unitarias completas y verificación técnica en Resolve.
- No incluye:
  - Creación de nuevos modelos 3D o diseño de nuevos personajes (se usan los assets existentes en `D:\Imágenes\01_Branding\@ely_vtuber\...`).
  - Sustitución de la pista nativa de subtítulos estática `ST1` para casos donde el usuario explícitamente elija traducción plana sin animación.

## Enfoque

1. **Investigación e ingeniería de plantillas**:
   - Mapear el catálogo de plantillas `.drb` y `.setting` (`SC-87-Impact Statement` y `Statement.setting`) accesibles en el sistema.
   - Definir el adaptador de inyección que permita insertar el clip con duración exacta (frames), pista destino (`V3`) y asignación de `StyledText`.
2. **Motor de sincronización SFX para Shorts**:
   - Mapear las entradas de clips en `V4` (expresiones) y calcular el fotograma de inyección en `A4`.
   - Emparejar tipo de evento (cambio sutil -> `pop`, reacción -> `bubble`, movimiento/giro -> `swoosh`).
3. **Refactorización de TimelineWriter en DaVinci Flow**:
   - Desacoplar el viejo método de carriers `.avi` / `.mov` e integrar el soporte de Fusion Titles nativos y SFX directos.
4. **Verificación y validación**:
   - Pruebas automatizadas en `tests/`.
   - Validación técnica en línea de tiempo de prueba en DaVinci Resolve.

## Criterios de finalización

- [ ] Plantilla cinética `Statement` inyectable en pista `V3` con texto `StyledText` dinámico sin archivos `.mov` pre-renderizados.
- [ ] Duración y tiempos de subtítulo sincronizados con precisión de fotograma con la pista de voz (`A1`).
- [ ] Inserción de SFX en `A4` (`pop`, `swoosh`) alineada con las entradas de expresiones en `V4`.
- [ ] Batería de pruebas unitarias existentes y nuevas pasando al 100%.
- [ ] Evidencia documentada en `VALIDATION.md` y aprobación registrada en `APPROVAL.md`.

## Autorización

- [x] Plan aprobado para ejecución por Biglex (sesión 2026-09-24).
