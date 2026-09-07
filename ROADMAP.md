# 🎯 DaVinci Flow — Roadmap

Plan de trabajo, objetivos de producto y estado verificable del proyecto.

> Un build o una prueba simulada no equivalen a una función terminada. Un hito pasa a Completado únicamente después de la prueba real y la aprobación correspondiente.

## 🔴 Pendientes activos

### Secuencia vigente acordada el 6 de septiembre de 2026

Estos tres planes dirigen el trabajo nuevo, en este orden. La LLM es central para la propuesta editorial; las reglas locales pueden validar o servir como modo explícito de diagnóstico, pero no sustituyen silenciosamente ese análisis. El montaje y la limpieza de silencios se preparan antes en Resolve.

1. [Fase 1 — Subtítulos, LLM y plantillas reales](process/active/2026-09-06_fase-1_textos-llm-y-plantillas/PLAN.md): leer subtítulos del montaje, revisar decisiones y aplicar hasta tres capas independientes utilizando títulos instalados y composiciones del Media Pool. Primera tarea: auditar el recorrido y comprobar ambas fuentes con una muestra real.
2. [Fase 2 — Dos pistas de sonido y cierre funcional](process/active/2026-09-06_fase-2_sonido-y-cierre-funcional/PLAN.md): transiciones y énfasis, revisión sonora, regeneración por intervalo y deshacer. Depende de la aceptación de la muestra de fase 1.
3. [Fase 3 — Visuals desde una carpeta](process/active/2026-09-06_fase-3_visuals-desde-carpeta/PLAN.md): selección revisable de imágenes y vídeos aportados por Biglex. Futura; depende del cierre funcional de fase 2.

Cada carpeta contiene PLAN.md, TASKS.md, VALIDATION.md y APPROVAL.md. Fase 1: recorrido editorial y muestra real de 27 clips comprobados en Resolve; falta aceptación visual de Biglex. Consultar su HANDOFF.md para integrar fase 2. Biglex indicó que empieza fase 2 mientras prepara las pruebas; esto no cierra la validación de fase 1. La aprobación del rumbo no es aceptación del resultado.

### Antecedentes técnicos por reconciliar

Los procesos siguientes conservan su evidencia histórica y permanecen pausados como líneas independientes mientras se reconcilian sus tareas con las tres fases. No ejecutarlos en paralelo como hojas de ruta alternativas. No se archivan ni se declaran completados aquí.

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

## 🟡 Intermedio

Las casillas históricas siguientes describen implementaciones registradas, no aceptación funcional. Plantillas y controles se verifican en fase 1; SFX y regeneración en fase 2; el catálogo B-roll en fase 3. Artículo e integración con el ecosistema quedan después del cierre funcional.

- [x] **Rediseño visual y espaciado de controles en la UI (distribución espaciosa en filas)**:
  - Reorganizada la cabecera, selectores y opciones en filas claramente separadas con márgenes holgados en UIManager y Tkinter.
- [x] **Escaneo dinámico de modelos de IA (Gemini)**:
  - Implementado `list_available_gemini_models` para consultar dinámicamente mediante la API de Google los modelos disponibles con fallback a `gemini-2.5-flash`.
- [x] **Soporte de plantillas y presets Text+ por capa en Media Pool**:
  - Implementado mapeo de `template_media_item` y `layer_templates` en `timeline_writer.py` y `application.py`.
- [x] **Asistente contextual de B-Rolls y Assets de Sonido (`B-Roll & Asset Context Injector`)**:
  - Implementado escáner recursivo de carpetas de assets (`broll_catalog.py`), emparejador semántico y contextual heurístico/IA (`broll_matcher.py`), pista `DF_BROLL` en Resolve (`track_manager.py` / `timeline_writer.py`) y controles en la interfaz gráfica.
- [ ] Permitir editar, aprobar o desactivar cada bloque directamente en la tabla con selector de animación y SFX.
- [ ] Añadir preescucha, sustitución, ganancia y fundidos de SFX desde la interfaz nativa.
- [ ] Completar regeneración selectiva por intervalo sobre la línea de tiempo.
- [ ] Publicar artículo de divulgación y tutorial en Aurora Blog (`Aurora---Blog`).
- [ ] Evaluar la integración con el ecosistema Biglex cuando el MVP esté aprobado.

## ⚪ Descartado / En Pausa

- ⏸️ Transcripción local pesada con Whisper. El MVP aprovecha la transcripción nativa de Resolve o archivos SRT.
- ⏸️ Proveedores LLM adicionales. Se conserva el adaptador existente como punto de partida; el análisis LLM sí es parte central del objetivo vigente.
- ⏸️ Automatización de cortes y eliminación de silencios desde DaVinciFlow; el montaje se prepara en Resolve antes de generar.

## 🟢 Completado

- Ningún hito de producto está cerrado todavía. La base técnica está implementada, pero la aprobación visual y auditiva sigue pendiente.
