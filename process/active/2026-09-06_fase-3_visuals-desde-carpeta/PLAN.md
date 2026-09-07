# Fase 3 — Visuals desde una carpeta del usuario

- Fecha: 2026-09-06
- Estado: PLANIFICADO; ejecución no iniciada.
- Proyecto: D:\Proyectos\biglexj\DaVinciFlow
- Prioridad: 3 de 3. Futura: ejecutar después del cierre funcional de fase 2. El catálogo B-roll existente es una base por auditar, no evidencia de funcionalidad terminada.
- Entrada general: [ROADMAP](../../../ROADMAP.md).

## Objetivo

Proponer y colocar imágenes y vídeos proporcionados por Biglex según la narración, manteniendo revisión y control editorial.

## Alcance

Incluye carpeta local elegida, catálogo de imágenes/vídeos, metadatos, selección LLM, revisión y colocación reversible. Excluye búsqueda o descarga web, generación de medios y análisis multimodal automático en esta fase.

## Enfoque secuencial

1. Escanear la carpeta elegida y sus subcarpetas. Inventariar nombres, etiquetas, tipo, dimensiones y duración cuando estén disponibles; identificar archivos ausentes, duplicados o no compatibles.

2. Reutilizar assets/broll_catalog.py y broll_matcher.py donde corresponda, añadiendo soporte real para imágenes. No interpretar coincidencia de nombres como comprensión visual del archivo.

3. Dar a la LLM el catálogo y contexto narrativo; admitir explícitamente ninguna propuesta. Seleccionar exclusivamente IDs existentes con intervalo, motivo y fragmento de origen.

4. Permitir previsualizar, sustituir, desactivar y ajustar inicio/duración. Definir encuadre, escalado y recorte sin deformación; silenciar por defecto el audio de vídeos de apoyo.

5. Integrar pistas visuales dedicadas con un orden que no tape textos. Resolver duración insuficiente sin bucles, congelados o cambios de velocidad silenciosos.

6. Extender el mismo sistema de generación, huellas, regeneración y reversión. Si faltan etiquetas útiles, solicitar etiquetado; considerar análisis visual como trabajo posterior separado.

## Criterios de finalización

Todas las comprobaciones de [VALIDATION.md](VALIDATION.md) deben tener evidencia. La aceptación de Biglex se registra en [APPROVAL.md](APPROVAL.md), separada de la validación técnica. No avanzar de fase por tener pruebas simuladas en verde.

## Riesgos y límites

La API de Resolve y las plantillas concretas necesitan comprobación local; no declarar compatibilidad por inventario. Los datos, recursos o sesión que falten se registran como pendientes, no como aprobados. Mantener las capas de dominio, aplicación y adaptadores; reutilizar módulos actuales sin reescritura general.

## Autorización y entrega

Biglex confirmó el rumbo y solicitó los planes el 2026-09-06 para guiar a otros agentes. Este turno entrega documentación; no acredita implementación ni aceptación del resultado. No pedir nuevamente aprobación del rumbo ya acordado. Respetar la dependencia indicada y consultar solo decisiones nuevas que cambien el alcance.

Al retomar: leer ROADMAP, este plan y los tres documentos asociados; comprobar estado de Git; tomar la primera tarea pendiente. Actualizar tareas, evidencia y bloqueos al entregar, indicando exactamente qué falta. No sobrescribir cambios concurrentes ni publicar por implicación.

