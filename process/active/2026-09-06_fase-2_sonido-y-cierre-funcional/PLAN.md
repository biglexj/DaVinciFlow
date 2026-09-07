# Fase 2 — Dos pistas de sonido y cierre funcional

- Fecha: 2026-09-06
- Estado: PLANIFICADO; ejecución no iniciada.
- Proyecto: D:\Proyectos\biglexj\DaVinciFlow
- Prioridad: 2 de 3. Requiere fase 1 validada y aceptación de su muestra. Reutilizar su contrato editorial y sus plantillas compatibles.
- Entrada general: [ROADMAP](../../../ROADMAP.md).

## Objetivo

Completar un flujo utilizable de textos y sonidos, con revisión, regeneración por intervalo y deshacer seguro sobre un vídeo real.

## Alcance

Incluye biblioteca SFX acordada, dos pistas sonoras, decisiones LLM, preescucha, ganancia, fundidos, límites de densidad, regeneración selectiva y validación de vídeo completo. Excluye visuals, descarga de assets, cortes automáticos y publicación.

## Enfoque secuencial

1. Inventariar la biblioteca disponible y confirmar cuáles son los sonidos que se utilizarán. Los WAV procedurales actuales son candidatos técnicos, no una biblioteca editorial aceptada por defecto.

2. Separar transiciones y énfasis en DF_SFX_TRANSITIONS y DF_SFX_ACCENTS como nombres propuestos. Diseñar compatibilidad con la pista histórica DF_SFX y sus registros sin mover ni eliminar material existente indiscriminadamente.

3. La LLM propone sonido, recurso, instante, función y motivo usando catálogo y contexto. Un corte o silencio no obliga a añadir whoosh. Validar límites, repeticiones, solapamientos y duración del recurso.

4. Ofrecer preescucha, sustitución, desactivación, ganancia y fundidos. Mantener textos y sonidos en una única propuesta revisada y persistida.

5. Regenerar bloques o intervalos conservando elementos manuales y ejecuciones ajenas. Definir pertenencia de clips que cruzan límites, identidad estable y comportamiento ante fallos parciales.

6. Comprobar rendimiento y respuesta de la interfaz con una secuencia completa, después de aceptar la muestra. Registrar tiempo de análisis, aplicación, corrección y reproducción, sin fijar promesas de velocidad sin medición.

## Criterios de finalización

Todas las comprobaciones de [VALIDATION.md](VALIDATION.md) deben tener evidencia. La aceptación de Biglex se registra en [APPROVAL.md](APPROVAL.md), separada de la validación técnica. No avanzar de fase por tener pruebas simuladas en verde.

## Riesgos y límites

La API de Resolve y las plantillas concretas necesitan comprobación local; no declarar compatibilidad por inventario. Los datos, recursos o sesión que falten se registran como pendientes, no como aprobados. Mantener las capas de dominio, aplicación y adaptadores; reutilizar módulos actuales sin reescritura general.

## Autorización y entrega

Biglex confirmó el rumbo y solicitó los planes el 2026-09-06 para guiar a otros agentes. Este turno entrega documentación; no acredita implementación ni aceptación del resultado. No pedir nuevamente aprobación del rumbo ya acordado. Respetar la dependencia indicada y consultar solo decisiones nuevas que cambien el alcance.

Al retomar: leer ROADMAP, este plan y los tres documentos asociados; comprobar estado de Git; tomar la primera tarea pendiente. Actualizar tareas, evidencia y bloqueos al entregar, indicando exactamente qué falta. No sobrescribir cambios concurrentes ni publicar por implicación.

