# Fase 1 — Subtítulos, LLM y plantillas reales

- Fecha: 2026-09-06
- Estado: implementación y muestra técnica real comprobadas; aceptación visual de Biglex pendiente.
- Proyecto: D:\Proyectos\biglexj\DaVinciFlow
- Prioridad: 1 de 3. Primera fase. Comenzar por T01. No depende del cierre de los procesos históricos.
- Entrada general: [ROADMAP](../../../ROADMAP.md).

## Objetivo

Convertir un fragmento real de subtítulos de Resolve en una propuesta editorial revisable y generar hasta tres capas con plantillas reales de las dos fuentes del usuario.

## Alcance

Incluye montaje previamente preparado, subtítulos nativos, límites de cortes, contexto narrativo, LLM, revisión de texto y plantilla por bloque, inserción y reversión de la muestra. Excluye nuevos SFX, visuals, cortes automáticos, transcripción propia y publicación.

## Enfoque secuencial

1. Seleccionar una muestra orientativa de 30–60 segundos con frases cortas y largas, énfasis y cambios de idea. Registrar proyecto, secuencia, fps, resolución, pistas y rango; trabajar en una secuencia de prueba.

2. Inventariar por separado títulos instalados en Resolve y composiciones del Media Pool en DaVinci Flow. No confundir la bandeja del proyecto con una carpeta del sistema. Verificar las vías disponibles en la API y documentar cualquier preparación manual necesaria.

3. Probar una plantilla representativa de cada fuente: localizar controles de texto, preservar nodos y animación, adaptar duración y comprobar entrada/salida. Publicar una matriz de compatibilidad; no prometer soporte universal.

4. Leer texto y tiempos del montaje final. Conservar originales y huellas de secuencia; usar cortes como contexto, no como frontera obligatoria de frase. No inventar tiempos por palabra cuando solo existen tiempos por subtítulo.

5. Definir un contrato versionado con IDs de origen, intervalos, roles, texto, ID de plantilla compatible, motivo y estado de revisión. Permitir de una a tres capas: contexto, principal y énfasis. Validar cobertura textual sin omisiones o duplicaciones accidentales.

6. Usar la LLM como responsable de la propuesta editorial, con contexto de frases vecinas y catálogo limitado. El adaptador no escribe en Resolve. Validar respuesta, recursos y tiempos; registrar modelo y límites de solicitud. Un fallo de API se muestra como tal; un modo local debe ser explícito.

7. Permitir editar, activar o desactivar bloques y elegir plantilla por capa antes de generar. Persistir la propuesta revisada: generar debe aplicar esa versión y no solicitar decisiones nuevas.

8. Aplicar la muestra en DF_CONTEXT, DF_MAIN y DF_ACCENT, verificar duración y posición, registrar los elementos propios y permitir retirar esa ejecución. Detectar cambios de secuencia entre análisis y aplicación.

## Criterios de finalización

Todas las comprobaciones de [VALIDATION.md](VALIDATION.md) deben tener evidencia. La aceptación de Biglex se registra en [APPROVAL.md](APPROVAL.md), separada de la validación técnica. No avanzar de fase por tener pruebas simuladas en verde.

## Riesgos y límites

La API de Resolve y las plantillas concretas necesitan comprobación local; no declarar compatibilidad por inventario. Los datos, recursos o sesión que falten se registran como pendientes, no como aprobados. Mantener las capas de dominio, aplicación y adaptadores; reutilizar módulos actuales sin reescritura general.

## Autorización y entrega

Biglex confirmó el rumbo y solicitó los planes el 2026-09-06 para guiar a otros agentes. Este turno entrega documentación; no acredita implementación ni aceptación del resultado. No pedir nuevamente aprobación del rumbo ya acordado. Respetar la dependencia indicada y consultar solo decisiones nuevas que cambien el alcance.

Al retomar: leer ROADMAP, este plan y los tres documentos asociados; comprobar estado de Git; tomar la primera tarea pendiente. Actualizar tareas, evidencia y bloqueos al entregar, indicando exactamente qué falta. No sobrescribir cambios concurrentes ni publicar por implicación.
