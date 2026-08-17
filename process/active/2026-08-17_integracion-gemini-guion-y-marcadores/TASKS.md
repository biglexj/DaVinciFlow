# Integración de Gemini, Comparación con Guion Original, Corrección de Jergas/Marcas y Marcadores en Línea de Tiempo — Tareas

- Estado: `COMPLETED`

## Ejecución

- [x] T01 — Implementar `davinci_flow/ai/credentials.py` para gestión segura de claves API de Gemini (entorno, configuración local y máscara).
- [x] T02 — Implementar `davinci_flow/ai/client.py` con `GeminiClient` compatible con REST v1beta y salida JSON estructurada.
- [x] T03 — Implementar `davinci_flow/ai/aligner.py` con motor de alineación contra guion original, corrección de jergas/marcas y extracción de marcadores.
- [x] T04 — Implementar `davinci_flow/resolve/marker_writer.py` para inserción y limpieza de marcadores en la línea de tiempo de DaVinci Resolve.
- [x] T05 — Robustecer adaptadores de Resolve (`ResolveSubtitleReader` y `ResolveTimelineWriter` con timecodes y playhead seguro).
- [x] T06 — Integrar casos de uso en `davinci_flow/application.py` (`align_and_correct_subtitles`, `insert_ai_timeline_markers`, `plan_with_ai_correction`).
- [x] T07 — Extender la interfaz gráfica (`davinci_flow/ui/uimanager_window.py`) con sección para Guion, Glosario de marcas, API Key y botones de corrección/marcadores.
- [x] T08 — Extender CLI en `davinci_flow/__main__.py` con banderas `--script`, `--glossary`, `--gemini-key`, `--correct-ai` y `--add-markers`.
- [x] T09 — Crear `AI_MODELS.md` y actualizar perfil `.agents/rules/core_profile.md` y `ROADMAP.md`.
- [x] T10 — Crear suite de pruebas unitarias permanentes en `tests/test_ai_credentials.py`, `tests/test_gemini_client.py`, `tests/test_script_aligner.py`, `tests/test_marker_writer.py`, `tests/test_application_ai.py` y actualizar existentes.
- [x] T11 — Preparar la validación y ejecutar suite completa (82/82 tests pasando).

Las pruebas no se documentan aquí. Deben registrarse en `VALIDATION.md`.
