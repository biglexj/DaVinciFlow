# 2026-10-21_integracion-mcp-minimax-y-capa-efectos — Tareas

- Estado: `COMPLETADO`

## Tareas

- [x] T01 — Crear `src/davinci_flow/ai/providers/` con `TextProvider` (protocolo), `GeminiProvider` (delegado en `GeminiClient`) y `MinimaxProvider` (chat completion v2, 3 reintentos en 5xx, 60 s, sin cambio silencioso de modelo).
- [x] T02 — Fábrica `build_text_provider()` y registro de proveedores; `preferences.provider` (`gemini` / `minimax`) con validación y compatibilidad con preferencias existentes.
- [x] T03 — Credenciales de Minimax en `ai/credentials.py` (mismo `config.json`, entorno `MINIMAX_API_KEY`, enmascarado, permisos restrictivos).
- [x] T04 — `src/davinci_flow/voice/tts.py`: locución Minimax (`t2a_v2`), decodificación hexadecimal, escritura a disco, extracción de subtítulos alineados desde `subtitle_file`.
- [x] T05 — `src/davinci_flow/subtitles/autocorrect.py`: normalización + glosario + corrección IA, con diff por subtítulo y etapas reportadas por separado.
- [x] T06 — `src/davinci_flow/resolve/subtitle_writer.py`: escritura de cues en pista nativa `subtitle` con verificación posterior y salida `.srt` garantizada.
- [x] T07 — `src/davinci_flow/resolve/fusion_effects.py`: generación de composiciones Fusion `.setting` parametrizadas, importación al Media Pool y anexado a la línea de tiempo como composición editable.
- [x] T08 — `src/davinci_flow/mcp_server.py`: servidor MCP por stdio con 13 herramientas (estado, captura, plantillas, propuesta, aplicación, deshacer, título nativo, efecto Fusion, voz, autocorrector, subtítulos, consulta de la API de scripting y sus documentos).
- [x] T09 — Panel de Ajustes: selector de proveedor, clave por proveedor, modelos por proveedor y tarjeta de voz con locución.
- [x] T10 — Pruebas unitarias de cada módulo nuevo y ejecución de la suite completa (329 en verde).
- [x] T11 — Documentación: `AI_MODELS.md`, `README.md`, `ROADMAP.md`, `docs/MCP_SERVIDOR.md` y `VALIDATION.md` con la evidencia real.

## Notas de ejecución

- No se tocó ningún archivo del proceso `2026-10-11_titulos-nativos-integrados-davinci`
  salvo `editorial/controller.py`, donde el cambio se limita a la fábrica de proveedor
  (import + dos llamadas) y convive con el trabajo ajeno en otras regiones del archivo.
- Las tres verificaciones en vivo (efecto Fusion, subtítulos nativos y llamada real a
  Minimax) quedan pendientes porque Resolve estaba cerrado; el procedimiento está en
  `VALIDATION.md`.
