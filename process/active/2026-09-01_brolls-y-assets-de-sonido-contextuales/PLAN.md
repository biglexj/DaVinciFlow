# 📋 Plan — Asistente Contextual de B-Rolls y Assets de Sonido

- **Objetivo**: Implementar un motor de análisis contextual asistido por IA y escáner de assets del usuario para sugerir y colocar automáticamente clips de apoyo (B-Rolls) y sonidos contextuales sobre la línea de tiempo de DaVinci Resolve.
- **Responsable**: biglexj / Antigravity
- **Fecha de inicio**: 2026-09-01
- **Estado**: En progreso

## Alcance
1. Escaneo e indexación de carpetas de recursos del usuario (vídeos `.mp4`/`.mov`, audios `.wav`/`.mp3`).
2. Extracción de metadatos y etiquetas léxicas a partir de nombres de carpetas y archivos.
3. Emparejamiento semántico (heurístico y con IA de Gemini) entre transcripción y assets.
4. Soporte para inserción en la pista dedicada `DF_BROLL` y `DF_SFX` en Resolve.
5. Controles en la interfaz gráfica (UIManager y Tkinter).
