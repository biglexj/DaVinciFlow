# 📝 Tareas — Animaciones Fusion, SFX en Pausas y Marcadores Cromáticos

- [x] **Documentación & Guía Editorial**: Redactar `docs/es/guides/flujo-de-trabajo-y-marcadores.md` y actualizar `ROADMAP.md`.
- [x] **Generador Fusion Paramétrico**: Implementar soporte para `pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse` y `typewriter` (WriteOn) en `src/davinci_flow/generation/fusion_template.py`.
- [x] **Detección de Pausas y Catálogo SFX Extendido**: Implementar triggers de pausas y 4 nuevos samplers de audio procedurale (`riser`, `glitch`, `thud`, `chime_success`) en `src/davinci_flow/sfx/`.
- [x] **Exportación SRT y Plan**: Implementar `export_srt_file`, `export_cues_to_srt_content` y `export_blocks_to_srt_content` en `src/davinci_flow/subtitles/srt_parser.py`.
- [x] **Integración UI Responsiva & Controles Interactivos**: Añadir combo de animación, botón Exportar SRT y visualización de animación en tabla de `uimanager_window.py`.
- [x] **Escáner y Presets de Bandeja Media Pool**: Implementar `template_scanner.py` para descubrir y aplicar automáticamente todas las plantillas Fusion/Text+ dentro de la bandeja `DaVinciFlow` del Media Pool.
- [x] **Lector Universal de Texto y Subtítulos**: Soporte para pistas de subtítulos nativas, pistas de vídeo con Text+/Fusion y modo automático en `subtitle_reader.py`.
- [x] **Pruebas Automatizadas**: Añadir pruebas unitarias para scanner de templates y lectura de vídeo tracks (**108/108 pruebas pasando al 100% en verde**).
- [x] **Validación y Registro**: Documentar resultados en `VALIDATION.md` y preparar `APPROVAL.md`.
