# 2026-10-21_integracion-mcp-minimax-y-capa-efectos — Plan

- Estado: `APPROVED` (ejecución autónoma por indicación explícita de Biglex: «No me preguntes nada. Te dejo con la tarea y tú lo culminas»).
- Responsable: `biglexj`
- Fecha de inicio: `2026-10-21`

## Objetivo

Convertir DaVinci Flow en una **herramienta completa** y no en un simple insestor de subtítulos:

1. **Proveedor de IA ampliable.** Habilitar la API de Minimax (texto) junto a Gemini, con adaptadores independientes del proveedor.
2. **Integración profunda con el MCP de DaVinci Resolve.** Dejar de usar el MCP oficial solo como pasamanos de `run_script_unsafe` y aprovechar su superficie real: descubrimiento de la API de scripting, generación de LUT/DCTL y operaciones de línea de tiempo.
3. **Creación automática de efectos.** Generar composiciones Fusion editables (`.setting`) e insertarlas en la línea de tiempo sin «horneado»: el usuario debe poder seguir editando texto, color, posición y animación en el Inspector.
4. **Voz.** Sintetizar locución con Minimax TTS y obtener subtítulos alineados a partir de la propia voz.
5. **Autocorrector.** Un corrector determinista + IA, con diff auditable por subtítulo.
6. **Subtítulos.** Escribir subtítulos en la pista nativa de subtítulos de Resolve, no solo como títulos Fusion.
7. **Exposición como herramienta.** Servidor MCP propio que publica estas operaciones para que cualquier agente pueda operatedar DaVinci Flow.

## Restricciones de no colisión

Otro agente trabaja en `process/active/2026-10-11_titulos-nativos-integrados-davinci/`. Se declara **territorio exclusivo del otro agente** (no se tocan):

`src/davinci_flow/resolve/kinetic_titles.py`, `src/davinci_flow/resolve/timeline_writer.py`, `src/davinci_flow/editorial/controller.py`, `src/davinci_flow/editorial/model.py`, `src/davinci_flow/editorial/writer.py`, `src/davinci_flow/editorial/template_files.py`, `src-flet/features/catalog/catalog_view.py`, `tests/test_kinetic_titles.py`, `tests/test_native_resolve_titles.py`.

Este proceso solo crea archivos nuevos y toca, como máximo, `editorial/preferences.py` y `editorial/controller.py` de forma quirúrgica (una fábrica de proveedor). Si el otro agente sobrescribe esas líneas, la functionality queda en `davinci_flow.ai.providers` y se reengancha en un solo punto.

## Decisiones de diseño

| Decisión | Motivo | Evidencia |
| --- | --- | --- |
| Capa `ai/providers/` con `TextProvider` | Regla local: «adaptadores independientes del proveedor» | `.agents/rules/base.md` |
| Minimax por `POST https://api.minimax.io/v1/text/chatcompletion_v2` | Endpoint oficial con formato compatible OpenAI | `platform.minimax.io/docs/api-reference/text-post` |
| Voz por `POST https://api.minimax.io/v1/t2a_v2` | Endpoint oficial, audio hexadecimal + `subtitle_file` | `platform.minimax.io/docs/api-reference/speech-t2a-http` |
| Sin `response_format` en Minimax | La API solo admite `json_schema` en `MiniMax-Text-01`; el JSON se fuerza por prompt y se sanea | Referencia oficial de `ChatCompletionReq` |
| Composición Fusion como `.setting` importable | Es lo único que llega a la línea de tiempo **editable**, no renderizado | `generation/fusion_template.py` existente |
| Subtítulos vía `.srt` → Media Pool → pista `subtitle` | La API de scripting 21.1 **no expone** creación de cues; solo `CreateSubtitlesFromAudio` | `DaVinciResolveScript.pyi` (Timeline, TrackType) |
| Servidor MCP propio sobre el MCP oficial | Reutiliza el puente y sus garantías (revisión obligatoria, sin reintentos de escritura) | `editorial/mcp_bridge.py` |

## Riesgos y mitigación

- **R1 — La API de scripting no documenta `mediaType` para subtítulos.** Mitigación: la escritura intenta variantes y **verifica** leyendo la pista; si ninguna funciona, deja el `.srt` en disco y lo reporta con la ruta exacta.
- **R2 — Resolve no está abierto en la máquina al momento de la ejecución.** Mitigación: toda escritura queda cubierta por pruebas con dobles; la verificación en vivo se registra como pendiente con pasos exactos en `VALIDATION.md`.
- **R3 — Modelos de MiniMax pueden envolver el JSON.** Mitigación: saneado de vallas ```` ```json ```` y extracción del primer objeto balanceado.

## Entregables

1. `src/davinci_flow/ai/providers/` — `base.py`, `gemini_provider.py`, `minimax_provider.py`, `factory.py`.
2. `src/davinci_flow/ai/credentials.py` — clave de Minimax en el mismo `config.json`.
3. `src/davinci_flow/editorial/preferences.py` — campo `provider`.
4. `src/davinci_flow/voice/tts.py` — locución Minimax con subtítulos alineados.
5. `src/davinci_flow/subtitles/autocorrect.py` — autocorrector con diff.
6. `src/davinci_flow/resolve/subtitle_writer.py` — escritura en pista nativa.
7. `src/davinci_flow/resolve/fusion_effects.py` — efectos Fusion editables.
8. `src/davinci_flow/mcp_server.py` — DaVinci Flow como herramienta MCP.
9. `src-flet/features/settings/settings_view.py` — proveedor, clave y voz.
10. Pruebas en `tests/` y documentación actualizada.
