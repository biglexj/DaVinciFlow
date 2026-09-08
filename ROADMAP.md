# 🎯 DaVinci Flow — Roadmap

Plan de trabajo, objetivos de producto y hoja de ruta estratégica del proyecto.

> **Regla del roadmap:** El Roadmap reúne los pendientes, prioridades, pausas y logros del producto. La ejecución detallada se registra dentro de `process/active/YYYY-MM-DD_objetivo/`. Cuando un proceso queda aprobado, el elemento correspondiente pasa a **Completado** (`- [x] **vX.X.X**`).

---

## 🔴 Pendientes activos

- [ ] **Fase 1 — Subtítulos, LLM y plantillas reales** — `process/active/2026-09-06_fase-1_textos-llm-y-plantillas/`
  - Lectura de subtítulos desde montaje, toma de decisiones con LLM y asignación a 3 capas independientes (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) mediante plantillas del sistema y Media Pool.
  - Estado: Muestra real de 27 clips comprobada en Resolve Studio 21; pendiente aceptación visual y auditiva final de Biglex.
- [ ] **Fase 2 — Dos pistas de sonido y cierre funcional** — `process/active/2026-09-06_fase-2_sonido-y-cierre-funcional/`
  - Transiciones y énfasis auditivo coordinado, revisión sonora, regeneración selectiva por intervalo y deshecho atómico.
  - Estado: En preparación técnica; depende de la aceptación de la muestra de Fase 1.
- [ ] **Fase 3 — Visuals desde una carpeta** — `process/active/2026-09-06_fase-3_visuals-desde-carpeta/`
  - Escaneo recursivo y selección revisable de imágenes y vídeos provistos localmente para inserción en la pista `DF_BROLL`.
  - Estado: Futura; planificada para iniciar tras el cierre funcional de Fase 2.
- [ ] **Diseño visual, biblioteca de plantillas y catálogo de medios** — `process/active/2026-09-07_relevo-diseno-y-biblioteca/`
  - Refinamiento de la interfaz desacoplada Flet con navegación por pestañas (`editor`, `catalog`, `library`, `settings`), previsualización de composiciones y selección granular.
- [ ] **Previsualización offline (dry-run con SRT sin Resolve)** — `process/active/2026-08-24_dry-run-offline-srt/`
  - Generación de registros y previsualizaciones (`--generate --dry-run --srt`) sin requerir una sesión activa de DaVinci Resolve.
  - Verificado: 97/97 pruebas automatizadas en verde; pendiente validación funcional con usuario.

---

## 🟡 Intermedio (Prioridad Media/Baja)

- [ ] Permitir editar, aprobar o desactivar cada bloque directamente en la tabla de la interfaz con selector de animación y SFX.
- [ ] Añadir preescucha, sustitución rápida, ajuste de ganancia y curvas de fundido de SFX desde la interfaz gráfica.
- [ ] Completar regeneración selectiva por intervalo temporal sobre la línea de tiempo activa.
- [ ] Redactar y publicar artículo de divulgación técnica y tutorial en Aurora Blog (`Aurora---Blog`).
- [ ] Evaluar e implementar la integración profunda con el ecosistema de aplicaciones Biglex tras la aprobación del MVP.

---

## ⚪ Descartado / En Pausa

- ⏸️ **Transcripción local pesada con Whisper**: El MVP aprovecha la transcripción nativa de DaVinci Resolve Studio o archivos SRT generados previamente.
- ⏸️ **Proveedores LLM adicionales**: Se conserva el cliente unificado de Google Gemini con adaptador desacoplado; el análisis editorial por LLM es el núcleo vigente.
- ⏸️ **Automatización de cortes y limpieza de silencios desde DaVinci Flow**: El montaje base y el corte de pausas se realizan en la línea de tiempo de Resolve antes de iniciar la generación editorial.

---

## 🟢 Completado

- [x] **v0.3.0** (2026-09-07) — Reestructuración desacoplada (Patrón Tauri & Screaming Architecture) y entorno único con uv
  - Desacoplamiento estructural en dos raíces maestras: backend puro sin dependencias gráficas (`src/davinci_flow/`) y frontend modular Flet (`src-flet/` estructurado en `app/`, `features/` [`editor`, `catalog`, `library`, `settings`] y `shared/`).
  - Consolidación del entorno en un único `.venv` oficial en CPython 3.13 de 64 bits gestionado por `uv`, erradicando la fragmentación y dependencias alternas de PyPy.
  - Lanzador de Resolve asíncrono no bloqueante (`desktop_launcher.py`) para evitar congelamientos en el hilo de edición de Resolve y scripts PowerShell de inicio rápido (`scripts/start-desktop.ps1`).
  - Validación técnica integral con 180/180 pruebas unitarias automatizadas superadas en verde.
- [x] **v0.2.0** (2026-09-06) — Editor editorial unificado, animaciones Fusion paramétricas, SFX procedural y marcadores cromáticos
  - Editor editorial unificado y toma de decisiones tipográficas asistidas por IA (Google Gemini) con distribución semántica multicapa (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`).
  - Motor de plantillas Fusion con curvas de interpolación Bézier (`pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse`, `typewriter`) y compatibilidad con `.setting`, `.comp` y `.drfx`.
  - Generador procedural de SFX (8 efectos esenciales: *whoosh*, *pop*, *bell*, *click*, *riser*, *glitch*, *thud*, *chime*) con detección automática de silencios en la pista `DF_SFX`.
  - Asistente contextual de B-Rolls (`DF_BROLL`) y catálogo de recursos audiovisuales locales con emparejamiento heurístico y semántico.
  - Estandarización de marcadores de Resolve por código cromático y redacción de guías técnicas oficiales (`docs/es/guides/editorial-fase-1.md` y `docs/es/guides/flujo-de-trabajo-y-marcadores.md`).
- [x] **v0.1.0** (2026-08-21) — Cierre inaugural de subtítulos dinámicos multicapa y alineación con guion original
  - Generación de subtítulos dinámicos multicapa en pistas no destructivas (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`, `DF_SFX`).
  - Lector híbrido resiliente para clips de subtítulos nativos en Resolve 21 y parser integrado de archivos SubRip (`.srt`).
  - Alineación semántica con guion original mediante la API de Google Gemini, corrección ortográfica fonética y glosario de términos.
  - Inserción automatizada de marcadores en línea de tiempo clasificados por relevancia temática y CLI completa con simulación (`--dry-run`) e idempotencia atómica (`--revert`).
