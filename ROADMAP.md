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
- [ ] **v0.2.0 — Animaciones Fusion paramétricas, SFX en pausas y marcadores cromáticos** — `process/active/2026-08-31_animaciones-fusion-sfx-pausas-y-marcadores/`
  - Motor de plantillas Fusion con keyframing Bezier (`pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse`).
  - Detección de silencios y pausas temporales para disparo automático de SFX de transición.
  - Estandarización de marcadores de Resolve por código cromático (Azul: Capítulos, Amarillo: Clave, Verde: SFX, Cian: Preguntas, Magenta: Corrección IA).
  - Guía técnica y editorial redactada para publicación en Aurora Blog (`docs/es/guides/flujo-de-trabajo-y-marcadores.md`).
- [ ] **Previsualización offline (dry-run con SRT sin Resolve)** — `process/active/2026-08-24_dry-run-offline-srt/`
  - `--generate --dry-run --srt` produce el record de previsualización sin exigir una sesión activa de Resolve.
  - Verificado: 97/97 pruebas automatizadas en verde.
  - Pendiente: validación funcional y aprobación de Biglex.

## 🟡 Siguientes mejoras

- [ ] Permitir editar, aprobar o desactivar cada bloque directamente en la tabla con selector de animación y SFX.
- [ ] Añadir preescucha, sustitución, ganancia y fundidos de SFX desde la interfaz nativa.
- [ ] Completar regeneración selectiva por intervalo sobre la línea de tiempo.
- [ ] Publicar artículo de divulgación y tutorial en Aurora Blog (`Aurora---Blog`).
- [ ] Evaluar la integración con el ecosistema Biglex cuando el MVP esté aprobado.

## ⚪ En pausa

- ⏸️ Transcripción local pesada con Whisper. El MVP aprovecha la transcripción nativa de Resolve o archivos SRT.
- ⏸️ Proveedores LLM adicionales. Gemini permanece detrás de un adaptador y no es requisito para el motor local.

## 🟢 Completado

- Ningún hito de producto está cerrado todavía. La base técnica está implementada, pero la aprobación visual y auditiva sigue pendiente.
