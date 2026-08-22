# 🎯 DaVinci Flow — Roadmap

Plan de trabajo, objetivos de producto y estado verificable del proyecto.

> Un build o una prueba simulada no equivalen a una función terminada. Un hito pasa a Completado únicamente después de la prueba real y la aprobación correspondiente.

## 🔴 Pendientes activos

- [ ] **v0.1.0 — Cierre funcional de transcripción, Fusion y SFX** — `process/active/2026-08-15_subtitulos-dinamicos-y-sfx/`
  - Lectura real aprobada técnicamente: 369 subtítulos de `Crear proyecto 1 / Timeline 1`.
  - Prueba vertical real aprobada técnicamente: tres capas Fusion y un SFX insertados, verificados y revertidos.
  - Pendiente: revisión visual y auditiva de Biglex antes de una generación completa.
- [ ] **Integración de Gemini, guion y marcadores** — `process/active/2026-08-17_integracion-gemini-guion-y-marcadores/`
  - Pruebas automatizadas correctas.
  - Pendiente: prueba real con API y aprobación del resultado.

## 🟡 Siguientes mejoras

- [ ] Permitir editar, aprobar o desactivar cada bloque directamente en la tabla.
- [ ] Añadir preescucha, sustitución, ganancia y fundidos de SFX desde la interfaz.
- [ ] Crear variantes visuales y transiciones automáticas para las plantillas Fusion.
- [ ] Completar regeneración selectiva por intervalo sobre la línea de tiempo.
- [ ] Evaluar la integración con el ecosistema Biglex cuando el MVP esté aprobado.

## ⚪ En pausa

- ⏸️ Transcripción local pesada con Whisper. El MVP aprovecha la transcripción nativa de Resolve o archivos SRT.
- ⏸️ Proveedores LLM adicionales. Gemini permanece detrás de un adaptador y no es requisito para el motor local.

## 🟢 Completado

- Ningún hito de producto está cerrado todavía. La base técnica está implementada, pero la aprobación visual y auditiva sigue pendiente.
