# Subtítulos dinámicos y SFX — Aprobación

- Estado: `PENDING`
- Este archivo concentra decisiones humanas; no se deben resolver por suposición.

## Aprobación del plan
 
- [x] Biglex aprueba comenzar por la Fase 0 y avanzar hacia el dominio y plan de generación (Instrucción explícita: 2026-08-15).
- [x] Se confirma que la fuente principal serán los subtítulos nativos de Resolve.
- [x] Se confirma la arquitectura modular en Python y plantillas Fusion propias.
- [x] Se confirma que la API de lenguaje es opcional y posterior al motor local.
 
 ## Decisiones visuales pendientes
 
 - [x] Identificar la fuente oficial de la paleta Aurora (`Aurora---Blog/frontend/src/styles/colors.css`).
 - [ ] Identificar las tipografías oficiales de Aurora.
 - [ ] Confirmar las tipografías permitidas para Ely.
 - [ ] Aprobar la primera plantilla visual mínima antes de crear variantes.
 - [ ] Decidir si la pista nativa de subtítulos queda visible u oculta después de generar.
 
 ## Decisiones editoriales pendientes
 
 - [ ] Aprobar los cinco perfiles iniciales o reducirlos para el MVP.
 - [ ] Definir cuántos bloques representativos se usarán para calibrar la clasificación.
 - [ ] Aprobar límites de densidad SFX después de revisar muestras reales.
 - [ ] Definir las categorías iniciales de SFX.
 - [ ] Confirmar cómo se marcan rangos reflexivos o excluidos.
 
 ## Decisiones técnicas pendientes
 
 - [x] Confirmar el comportamiento real de la API con Resolve 21.
 - [ ] Aprobar la estrategia de pistas calculadas frente a índices configurables.
 - [ ] Aprobar el formato persistente de `GenerationPlan` y `GenerationRecord`.
 - [ ] Elegir la tecnología de interfaz después de la prueba de `UIManager`.
 - [ ] Decidir si macOS entra en el MVP o en un hito posterior.
 
 ## Puertas por fase

- [x] G0 — Lectura real validada técnicamente: 369 subtítulos de `Crear proyecto 1 / Timeline 1`.
- [x] G1 — Dominio y plan de generación aprobados (validado con pruebas automatizadas unitarias).
- [ ] G2 — Prueba vertical Fusion validada técnicamente; aprobación visual de Biglex pendiente.
- [ ] G3 — Multicapa y Brand Guard validados en código; aprobación visual de los temas pendiente.
- [ ] G4 — Previsualización y deshacer selectivo validados; edición y regeneración física por bloque pendientes.
- [ ] G5 — Inserción real de SFX validada; preescucha, mezcla y aprobación auditiva pendientes.
- [ ] G6 — Interfaz abierta en Resolve; recorrido completo y aprobación de Biglex pendientes.
- [ ] G7 — API de lenguaje aprobada, aplazada o descartada explícitamente.

## Controles de cierre

- [x] Validación técnica del agente (95 pruebas y prueba vertical real reversible).
- [ ] Validación funcional sobre Resolve.
- [ ] Revisión visual de Biglex.
- [x] `ROADMAP.md` actualizado.
- [x] Documentación de uso e instalación actualizada.
- [x] Recursos procedurales y licencias revisados.
- [ ] Aprobación final de Biglex.

## Decisión

- [ ] `APPROVED`
- [ ] `REWORK`
- [ ] `CANCELLED`
- [ ] `SUPERSEDED`

## Resumen

- Pendiente de completar al cerrar el proceso.

## Destino

- `APPROVED` con todos los controles completos → `process/completed/2026/`.
- `CANCELLED`, `SUPERSEDED` o cierre incompleto → `process/archive/2026/`.
- `REWORK` → permanece en `process/active/`.

Mover la carpeta completa y no conservar una copia duplicada en `active`.
