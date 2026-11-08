# Propuestas editoriales por lotes y reanudación — Tareas

- Estado: `IN_PROGRESS`

## Tareas

- [x] T01 — Incorporar metadatos de ventana de entrada/salida para modelos Gemini y filtro activable de contexto largo en Ajustes.
- [x] T02 — Habilitar Gemini 3.8 Flash con parámetros de generación compatibles con su API.
- [x] T03 — Extender el planificador para solicitudes configurables de hasta 500 cues o toda la secuencia, conservando el tope de caracteres.
- [x] T04 — Añadir captura completa, lotes manuales/automáticos, checkpoints atómicos y reanudación validada.
- [x] T05 — Reutilizar una propuesta parcial guardada cuando sus cues coincidan y producir una única propuesta final.
- [x] T06 — Añadir controles, progreso y estados claros en el editor sin habilitar aplicar una propuesta incompleta.
- [x] T07 — Compilar con `mise build` y registrar límites de validación en Resolve.
- [x] T08 — Vincular propuestas SRT a la línea activa solo cuando el proyecto y todos los cues coinciden en texto y tiempos.

## Estado de implementación

- Integración local terminada y compilada el `2026-11-06`.
- La escritura final y su deshacer quedan pendientes de la comprobación manual de Biglex en Resolve.

## Archivos reservados

No editar `src/davinci_flow/editorial/controller.py` ni `src/davinci_flow/editorial/model.py`; pertenecen al proceso activo de títulos nativos.
