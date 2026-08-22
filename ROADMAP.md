# 🎯 DaVinci Flow — Roadmap

Plan de trabajo, objetivos de producto y hoja de ruta estratégica del proyecto.

> **Regla del roadmap:** El Roadmap reúne los pendientes, prioridades, pausas y logros del producto. La ejecución detallada se registra dentro de `process/active/YYYY-MM-DD_objetivo/`. Cuando un proceso queda aprobado, el elemento correspondiente pasa a **Completado** (`- [x] **vX.X.X**`).

---

## 🔴 Pendientes activos

- [ ] **Sinergia con el Ecosistema Biglex (Web Launchpad & Aurora Synapse)** — `process/active/2026-08-21_interconexion-ecosistema-web/`
- [ ] **Plantillas Fusion Personalizables (.setting) para Ely y Aurora** — `process/active/2026-08-22_plantillas-fusion-setting/`

---

## 🟡 Intermedio (Prioridad Media/Baja)

- [ ] Generar títulos Fusion en capas de contexto, énfasis y complemento con transiciones automáticas.
- [ ] Incorporar una biblioteca SFX propia con previsualización y límites de densidad configurables.
- [ ] Diseñar el flujo guiado de análisis, revisión y regeneración selectiva por bloques.
- [ ] Integración con proveedores LLM alternativos mediante adaptadores independientes.

---

## ⚪ Descartado / En Pausa

- ⏸️ Transcripción local pesada en GPU con Whisper; DaVinci Flow aprovecha la transcripción nativa de Resolve, archivos SRT o la suite externa LyraFlow.

---

## 🟢 Completado

- [x] **v0.1.0 — Base técnica, lectura de subtítulos, IA con Gemini y marcadores** — `process/completed/2026/2026-08-17_integracion-gemini-guion-y-marcadores/`
  - Conexión local robusta con DaVinci Resolve 21 vía API de scripting.
  - Lector híbrido de subtítulos desde pista activa de Resolve y archivos `.SRT`.
  - Motor de clasificación de subtítulos multicapa (Contexto, Principal, Acento y SFX).
  - Integración de Google Gemini API para corrección con guion original y glosario de marcas/jergas.
  - Inserción automatizada de marcadores temáticos en la línea de tiempo.
  - Interfaz gráfica UIManager nativa de DaVinci y fallback Tkinter con paleta neutra `#202020`.
  - Suite de pruebas unitarias al 100% (87 tests aprobados).
