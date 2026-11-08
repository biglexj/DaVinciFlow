# 2026-10-21_integracion-mcp-minimax-y-capa-efectos — Validación

- Estado: `COMPLETADO_CON_VALIDACION_EN_VIVO_PENDIENTE`

## Matriz de Verificación

| Verificación | Método | Estado | Evidencia |
| :--- | :--- | :--- | :--- |
| `MinimaxProvider` construye la petición al endpoint oficial | Unit test | ✅ | `tests/test_ai_providers.py::test_request_uses_official_endpoint_and_headers` comprueba URL `https://api.minimax.io/v1/text/chatcompletion_v2`, cabecera `Bearer`, modelo y roles de los mensajes. |
| `MinimaxProvider` reintenta 5xx y respeta el modelo | Unit test | ✅ | `test_retries_on_server_error` (3 intentos ante 503) y `test_does_not_retry_on_client_error` (1 intento ante 400). |
| `MinimaxProvider` sanea JSON en vallas de código | Unit test | ✅ | `test_generate_json_parses_fenced_json` y `test_generate_json_raises_on_invalid_payload`. |
| `base_resp` con error lógico se reporta | Unit test | ✅ | `test_base_resp_error_is_reported` (código 2013). |
| La clave no aparece en los mensajes de error | Unit test | ✅ | `test_error_message_hides_credentials`. |
| `build_text_provider` resuelve por proveedor y modelo | Unit test | ✅ | `tests/test_ai_providers.py::ProviderFactoryTests`. |
| Preferencias con `provider` cargan configuraciones previas | Unit test | ✅ | `tests/test_ai_providers.py::PreferencesProviderTests` (legado → `gemini`; `minimax` restituye su modelo). |
| Credencial de Minimax: entorno, archivo y ausencia | Unit test | ✅ | `tests/test_ai_providers.py::MinimaxCredentialsTests`. |
| Locución: decodificación hexadecimal y metadatos | Unit test | ✅ | `tests/test_voice.py::SpeechClientTests` (audio, duración, formato, `trace_id`). |
| Locución: subtítulos alineados del archivo de Minimax | Unit test | ✅ | `tests/test_voice.py::SubtitleParsingTests` (lista, diccionario, segmentos inválidos). |
| Locución: catálogo de voces de la cuenta | Unit test | ✅ | `test_list_voices_parses_catalog`. |
| Autocorrector distingue etapa y produce diff | Unit test | ✅ | `tests/test_autocorrect.py` (normalización, glosario, IA; el diff indica la etapa que cambió cada línea). |
| La IA con índices incorrectos cancela la operación | Unit test | ✅ | `test_wrong_indices_cancel_the_operation` y `test_invalid_payload_cancels_the_operation`. |
| Escritura en pista nativa: variantes y verificación | Unit test | ✅ | `tests/test_subtitle_writer.py` (variante `mediaType` correcta, reintento y error con ruta del `.srt`). |
| Efecto Fusion `.setting` se genera con la estructura esperada | Unit test | ✅ | `tests/test_fusion_effects.py` (`TextPlus`, `MediaOut`, texto escapado, nodo `Glow` con salida reconectada). |
| Inserción de composición y de título nativo | Unit test | ✅ | `FusionEffectWriterTests` con doble de sesión (importación, anexado, pista, fotogramas). |
| Servidor MCP publica y despacha herramientas | Unit test | ✅ | `tests/test_mcp_server.py` (13 herramientas, `initialize`, `tools/list`, `tools/call`, error de herramienta y error inesperado). |
| Servidor MCP en ejecución real (stdio) | Prueba de humo | ✅ | `python -m davinci_flow.mcp_server` respondió `initialize`, `tools/list` (13 herramientas) y `tools/call` de `davinciflow_status`. |
| Regresión de la suite completa | Unit test | ✅ | **329 pruebas en verde**: 270 (`test_[a-r]*`) + 46 (`test_s*` sin `test_sfx_player`) + 13 (`test_v*`). |
| Interfaz de Ajustes con proveedor y voz | Unit test | ✅ | `tests/test_desktop.py` y `tests/test_subtitles_view.py` (47 pruebas) sin regresión tras el cambio de la vista. |
| Propuesta editorial con Minimax (contrato 1.1.0) | Prueba real | ⏳ | Requiere `MINIMAX_API_KEY` y la secuencia de trabajo. |
| Locución real con Minimax | Prueba real | ⏳ | Requiere `MINIMAX_API_KEY`. |
| Inserción de efecto Fusion en Resolve | En vivo | ⏳ | Requiere Resolve abierto. |
| Subtitulado nativo en Resolve | En vivo | ⏳ | Requiere Resolve abierto. |

## Observaciones de la ejecución

- **El servidor MCP de DaVinci Flow se verificó en ejecución real** sobre stdio: el
  handshake, el catálogo de herramientas y la llamada a `davinciflow_status` respondieron
  correctamente. La herramienta devolvió el estado del puente oficial:

  ```json
  {
    "proveedor": "gemini",
    "modelo": "gemini-3.5-flash-lite",
    "credenciales": { "gemini": true, "minimax": false },
    "resolve": {
      "transport": "mcp",
      "executable": "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\ResolveMCP.exe",
      "server": { "name": "davinci_resolve", "version": "21.1" },
      "running": false,
      "version": "21.1"
    }
  }
  ```

  Es decir: el flujo llega al **MCP oficial de Resolve 21.1** (`davinci_resolve`), y
  `running: false` confirma que la aplicación estaba cerrada durante la sesión.
- **`test_sfx_player` se cuelga y es ajeno a este proceso.** El módulo `src/davinci_flow/sfx/player.py`
  no aparece en `git diff` (está intacto) y el bloqueo ocurre dentro de su prueba de
  reproducción de audio con MCI en Windows. Se ejecutó la suite completa en tres partes
  para obtener un resultado reproducible: **329 pruebas, 0 fallos**.
- **La API de scripting de Resolve 21.1 no permite crear cues de subtítulo.** El stub
  oficial solo expone `CreateSubtitlesFromAudio` (subtitulado automático). El camino
  soportado es escribir un `.srt`, importarlo al Media Pool y anexarlo a una pista de
  tipo `subtitle`. Como `mediaType` solo documenta vídeo (1) y audio (2), el escritor
  prueba variantes y **verifica** la pista; si ninguna funciona, deja el `.srt` en disco
  e informa de la ruta exacta para importarlo a mano.
- **`git diff --check` reporta un espacio final en `src/davinci_flow/editorial/writer.py:363`.**
  Ese archivo pertenece al proceso `2026-10-11_titulos-nativos-integrados-davinci`
  (otro agente) y no se tocó para evitar una colisión de escritura.
- **Resolve estaba cerrado durante la ejecución**, por lo que las tres verificaciones en
  vivo quedan pendientes con el procedimiento descrito abajo.

## Procedimiento para la verificación en vivo

1. Abrir DaVinci Resolve Studio 21.1 con un proyecto y una secuencia, y esperar a que
   el MCP oficial responda (`davinciflow_status` debe mostrar `transport: mcp`).
2. **Efecto Fusion editable**:
   `davinciflow_create_fusion_effect` con `{"text": "Prueba", "animation_preset": "fade_smooth", "start_frame": 0, "duration_frames": 120}`.
   Verificar en el Inspector que el `Text+` aparece con su `StyledText` editable y que la
   composición sigue siendo un objeto Fusion (no un render).
3. **Título nativo**:
   `davinciflow_insert_native_title` con `{"template_name": "Text+", "start_frame": 0, "duration_frames": 120}`.
4. **Subtítulos nativos**:
   `davinciflow_write_subtitles` con dos cues (`start_frame`/`end_frame`). Si la
   confirmación es `false`, leer el `srt_path` devuelto e importarlo a mano para
   confirmar la hipótesis de la variante de `mediaType`.
5. **Locución real**: configurar `MINIMAX_API_KEY` en Ajustes y usar
   `davinciflow_synthesize_speech`; comprobar que el archivo de audio se guarda y que la
   lista de subtítulos alineados es coherente con la locución.
6. **Propuesta editorial con Minimax**: seleccionar el proveedor Minimax en Ajustes y
   ejecutar `davinciflow_propose`; comprobar que la propuesta respeta el contrato 1.1.0
   antes de `davinciflow_apply` con `reviewed: true`.
