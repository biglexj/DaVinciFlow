# Estilo tipográfico multicapa y adaptación de encuadre — Plan

- Estado: `IN_PROGRESS`
- Fecha: `2026-09-10`
- Proyecto: `DaVinci Flow`
- Enlace: `process/active/2026-09-06_fase-1_textos-llm-y-plantillas/` (Cierre de revisión visual V07 / T08)

## Objetivo

Actualizar las plantillas Fusion `.setting` básicas a estándares de alto impacto visual (estilo Franz Goñas / YouTube / Reels con sombreado 3D nativo, contorno y contraste cromático dorado/blanco), e instruir al modelo Gemini con criterio de director tipográfico consciente de la orientación de pantalla (vertical 9:16 vs. horizontal 16:9) y jerarquía de hasta 3 capas.

## Alcance

- Incluye:
  - Rediseño de las plantillas `.setting` en `src/davinci_flow/editorial/basic_titles/` (`Contexto`, `Principal` y `Énfasis`) con tipografía moderna (`Montserrat`), sombreado multicapa de Fusion (`Shading` de `TextPlus`: relleno, trazo/borde negro de alto contraste y sombra suave de profundidad) y color contrastante dorado/amarillo (`#FFBC00`) en la capa de Énfasis.
  - Calibración de posiciones verticales (`Center`) para formar bloques compactos y cohesivos (1, 2 o 3 líneas agrupadas) sin dispersión vertical desmedida.
  - Actualización del prompt del LLM en `src/davinci_flow/editorial/planner.py` para erradicar la restricción de "una sola capa para frases breves", inyectar la orientación (`vertical` vs. `horizontal`) y guiar la distribución en hasta 3 capas.
  - Pruebas unitarias de integridad de plantillas y propuesta LLM.
- No incluye:
  - Inserción de SFX en la línea de tiempo (corresponde al inicio de Fase 2 en `process/active/2026-09-06_fase-2_sonido-y-cierre-funcional/`).

## Enfoque

1. Rediseñar `Text+ básico - Contexto.setting`, `Text+ básico - Principal.setting` y `Text+ básico - Énfasis.setting` con estilos Fusion profesionales (`Shading`, colores, trazo, sombra y espaciado).
2. Incorporar detección y directivas de orientación vertical/horizontal en `planner.py` y actualizar el prompt editorial.
3. Ejecutar y validar con la suite de pruebas automatizadas.

## Criterios de finalización

- [ ] Las 3 plantillas básicas contienen configuración de sombreado profesional (borde negro + sombra) y contraste dorado (`#FFBC00`) en la capa de Énfasis.
- [ ] Las posiciones verticales forman un bloque armónico agrupado en el centro/zona segura.
- [ ] El prompt editorial incluye la orientación de encuadre (vertical u horizontal) y directivas de jerarquía tipográfica para 1 a 3 capas.
- [ ] 223+ pruebas unitarias pasan limpiamente en verde.

## Autorización

- [x] Rumbo aprobado explícitamente por Biglex el 2026-09-10.
