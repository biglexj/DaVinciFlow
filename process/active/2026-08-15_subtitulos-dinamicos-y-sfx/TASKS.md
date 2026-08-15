# Subtítulos dinámicos y SFX — Tareas

- Estado: `PENDING`
- Regla: trabajar en orden y no comenzar una fase cuya puerta precedente esté pendiente.

## Dependencia previa

- [ ] T00.1 — Abrir Resolve 21 con un proyecto de prueba y una pista de subtítulos nativa.
- [ ] T00.2 — Completar la validación real del proceso `2026-08-15_base-inicial`.
- [ ] T00.3 — Registrar la aprobación de G0 antes de crear capacidades de escritura.

## Fase 1 — Dominio y plan de generación

- [x] T01.1 — Definir `CaptionBlock` con roles opcionales y trazabilidad hacia el subtítulo original.
- [x] T01.2 — Definir `GenerationPlan` versionado, serializable y sin objetos de Resolve.
- [x] T01.3 — Normalizar espacios y puntuación sin perder tildes, eñes, números o nombres propios.
- [x] T01.4 — Implementar reglas deterministas para una, dos o tres capas.
- [x] T01.5 — Registrar el motivo y la confianza de cada clasificación.
- [x] T01.6 — Crear huellas estables de texto, rango y configuración.
- [x] T01.7 — Añadir pruebas de frases cortas, largas, preguntas, cifras, negaciones y signos.
- [x] T01.8 — Validar serialización y compatibilidad del formato del plan.
- [x] T01.9 — Completar V1 y solicitar aprobación G1.

## Fase 2 — Prueba vertical de Fusion

- [ ] T02.1 — Comprobar desde Python qué títulos Fusion reconoce Resolve 21.
- [ ] T02.2 — Crear una plantilla propia mínima sin adoptar branding externo.
- [ ] T02.3 — Insertar un bloque en una copia de la línea de tiempo.
- [ ] T02.4 — Ajustar texto, inicio, final y duración mediante la API disponible.
- [ ] T02.5 — Registrar el elemento creado y retirarlo de forma segura.
- [ ] T02.6 — Probar fallos: pista bloqueada, plantilla ausente y rango inválido.
- [ ] T02.7 — Completar V2 y solicitar aprobación G2.

## Fase 3 — Multicapa y Brand Guard

- [ ] T03.1 — Definir pistas lógicas sin asumir índices físicos fijos.
- [ ] T03.2 — Crear o reutilizar `DF_CONTEXT`, `DF_MAIN` y `DF_ACCENT`.
- [ ] T03.3 — Implementar bloques de una, dos y tres capas.
- [ ] T03.4 — Definir el contrato `ThemeTokens`.
- [ ] T03.5 — Cargar la fuente oficial de colores y tipografías de Aurora.
- [ ] T03.6 — Materializar el tema Ely desde su paleta oficial.
- [ ] T03.7 — Rechazar valores visuales no permitidos.
- [ ] T03.8 — Implementar posiciones seguras horizontal y vertical.
- [ ] T03.9 — Impedir duplicados al ejecutar dos veces el mismo plan.
- [ ] T03.10 — Completar V3 y solicitar aprobación G3.

## Fase 4 — Previsualización y regeneración

- [ ] T04.1 — Crear el modo de análisis sin escritura.
- [ ] T04.2 — Mostrar roles, tiempos, tema, confianza y motivos por bloque.
- [ ] T04.3 — Permitir aprobar, desactivar o corregir bloques.
- [ ] T04.4 — Añadir marcadores propios solo si la prueba vertical confirma su utilidad.
- [ ] T04.5 — Registrar ejecuciones y elementos generados.
- [ ] T04.6 — Detectar subtítulos nuevos, modificados y eliminados.
- [ ] T04.7 — Regenerar un intervalo sin tocar los demás bloques.
- [ ] T04.8 — Retirar únicamente una ejecución seleccionada.
- [ ] T04.9 — Recuperarse de una generación interrumpida.
- [ ] T04.10 — Completar V4 y solicitar aprobación G4.

## Fase 5 — Motor SFX

- [ ] T05.1 — Definir el esquema de `AssetDescriptor`.
- [ ] T05.2 — Preparar una biblioteca mínima con autoría, licencia y fuente verificables.
- [ ] T05.3 — Clasificar SFX por intención y no únicamente por intervalo temporal.
- [ ] T05.4 — Implementar límites de densidad, reutilización y exclusión.
- [ ] T05.5 — Crear o reutilizar la pista `DF_SFX`.
- [ ] T05.6 — Insertar un SFX aprobado en el tiempo correcto.
- [ ] T05.7 — Configurar ganancia y fundidos compatibles con la API real.
- [ ] T05.8 — Permitir preescucha, sustitución y desactivación.
- [ ] T05.9 — Probar rangos reflexivos y `SFX_OFF`.
- [ ] T05.10 — Completar V5 y solicitar aprobación G5.

## Fase 6 — Interfaz guiada

- [ ] T06.1 — Validar `UIManager` o la alternativa oficial disponible desde Python.
- [ ] T06.2 — Crear un iniciador pequeño para el menú de Resolve.
- [ ] T06.3 — Implementar el paso Fuente.
- [ ] T06.4 — Implementar el paso Tema y perfil.
- [ ] T06.5 — Implementar el paso Análisis y revisión.
- [ ] T06.6 — Implementar el paso SFX.
- [ ] T06.7 — Implementar el resumen y la generación.
- [ ] T06.8 — Mostrar progreso, cancelación y errores recuperables.
- [ ] T06.9 — Incorporar información de versión, autoría, licencia y enlaces oficiales cuando exista una UI distribuible.
- [ ] T06.10 — Completar V6 y solicitar aprobación G6.

## Fase 7 — Evaluación opcional de API de lenguaje

- [ ] T07.1 — Medir la calidad de las reglas locales con un conjunto representativo.
- [ ] T07.2 — Definir el esquema estructurado y el contrato independiente del proveedor.
- [ ] T07.3 — Definir privacidad, presupuesto, tiempo límite, caché y respaldo.
- [ ] T07.4 — Comparar precisión, latencia y coste frente al motor local.
- [ ] T07.5 — Crear `AI_MODELS.md` únicamente si la función se adopta.
- [ ] T07.6 — Registrar la decisión: adoptar, aplazar o descartar.
- [ ] T07.7 — Solicitar aprobación G7 si se propone activarla.

## Cierre

- [ ] TC.1 — Actualizar README, ROADMAP y notas sin anunciar una publicación inexistente.
- [ ] TC.2 — Ejecutar toda la matriz automatizada.
- [ ] TC.3 — Completar las pruebas manuales en Resolve.
- [ ] TC.4 — Confirmar que no quedan claves, rutas privadas o recursos sin licencia.
- [ ] TC.5 — Obtener aprobación final de Biglex.
- [ ] TC.6 — Mover el proceso a `process/completed/2026/` únicamente tras la aprobación.
