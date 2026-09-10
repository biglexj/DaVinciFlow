# Validación

- El servidor instalado responde como `davinci_resolve`, versión `21.1`.
- `run_script_unsafe` importa el paquete local con el Python integrado y obtiene la sesión sin cargar la DLL en DaVinci Flow.
- La primera captura detectó que Resolve 21.1 incluye transiciones en `GetItemListInTrack`; sus offsets de origen son `None`. La captura anterior fallaba también con la conexión CPython.

## Comprobaciones finales

- [x] `python -m unittest discover -s tests -q`: 217 pruebas aprobadas.
- [x] `python -m compileall -q src/davinci_flow/resolve src/davinci_flow/editorial tests/test_mcp_bridge.py`.
- [x] `git diff --check` sin errores de espacios.
- [x] Pruebas con procesos JSON-RPC reales simulados: notificaciones, ruido nativo, EOF, timeout, contenido mal formado y errores incrustados.
- [x] Selección automática/forzada, ausencia de fallback tras fallo y rechazo de propuestas sin revisión antes de iniciar MCP.
- [x] Inyección de sesión sin reconectar a la DLL y nombres anteriores sin duplicación.

## Sesión real, 2026-09-10

Evidencia estructurada: [evidence.json](evidence.json). Resolve Studio `21.1.0.14`; servidor `davinci_resolve` `21.1`.

- Captura mediante `EditorialController.read_resolve`: proyecto Campaña, Timeline 1; 72 subtítulos, 65 elementos (15 transiciones), 2,455 segundos en la prueba final.
- Huella original antes y después: `392633a3d14b02d68f31a8e9bf104452935726fe1e8756b68bd9a4e9c71f70fe`.
- Copia temporal `DF_MCP_VALIDATION_791208a14e` y carpeta propia: un título básico Fusion generado por `resolve_bridge.apply`, 2,768 segundos.
- Lectura posterior por el MCP: texto exacto del primer subtítulo, pista DF_MAIN, inicio 5 y duración 21 fotogramas.
- Reaplicación: un único elemento. Deshacer: estado `reverted`; cero clips restantes en las pistas DF.
- Retirada confirmada de la secuencia y carpeta temporales; secuencia y carpeta originales restauradas.
- Diagnóstico independiente de SetName en secuencia temporal: `DF::short` y `DF:short` rechazados; nombre de 91 caracteres sin dos puntos aceptado. La corrección no depende de una conjetura sobre longitud.

## Límites pendientes

- No se generó ni aprobó una propuesta LLM para el montaje original. La muestra técnica utiliza un duplicado temporal.
- No se comprobó una generación extensa frente al máximo de 60 segundos por script del MCP. Las escrituras de resultado incierto no se repiten ni cambian de transporte.
- No se reclama aceptación visual/auditiva, mejora de rendimiento sostenida, pruebas macOS/Linux ni versión publicada.
- El controlador que utiliza Flet está validado; no se abrió una nueva ventana Flet para revisión visual en esta prueba.
