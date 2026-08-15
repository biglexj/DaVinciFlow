# Subtítulos dinámicos y SFX — Aprobación

- Estado: `PENDING`
- Este archivo concentra decisiones humanas; no se deben resolver por suposición.

## Aprobación del plan

- [ ] Biglex aprueba comenzar por la Fase 0.
- [ ] Se confirma que la fuente principal serán los subtítulos nativos de Resolve.
- [ ] Se confirma la arquitectura modular en Python y plantillas Fusion propias.
- [ ] Se confirma que la API de lenguaje es opcional y posterior al motor local.

## Decisiones visuales pendientes

- [ ] Identificar la fuente oficial de la paleta Aurora.
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

- [ ] Confirmar el comportamiento real de la API con Resolve 21.
- [ ] Aprobar la estrategia de pistas calculadas frente a índices configurables.
- [ ] Aprobar el formato persistente de `GenerationPlan` y `GenerationRecord`.
- [ ] Elegir la tecnología de interfaz después de la prueba de `UIManager`.
- [ ] Decidir si macOS entra en el MVP o en un hito posterior.

## Puertas por fase

- [ ] G0 — Lectura real de subtítulos aprobada.
- [ ] G1 — Dominio y plan de generación aprobados.
- [ ] G2 — Prueba vertical de Fusion aprobada.
- [ ] G3 — Multicapa y Brand Guard aprobados.
- [ ] G4 — Previsualización y regeneración aprobadas.
- [ ] G5 — Motor SFX aprobado.
- [ ] G6 — Interfaz guiada aprobada.
- [ ] G7 — API de lenguaje aprobada, aplazada o descartada explícitamente.

## Controles de cierre

- [ ] Validación técnica del agente.
- [ ] Validación funcional sobre Resolve.
- [ ] Revisión visual de Biglex.
- [ ] `ROADMAP.md` actualizado.
- [ ] Documentación de uso e instalación actualizada.
- [ ] Recursos y licencias revisados.
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
