# Modelos de IA de DaVinci Flow

Última actualización: 2026-09-08. Los identificadores de este registro describen el código local y las llamadas observadas; no garantizan disponibilidad futura del proveedor.

| Función | Modelo configurado | Evidencia |
|---|---|---|
| Propuesta editorial selectiva 1.1.0 | Modelo compartido desde Ajustes; preferencia comprobada `gemini-3.7-flash` | El 8 de septiembre, propuestas reales con tres subtítulos sintéticos validadas con 3.7 (dos intentos) y 3.8 (un intento). No se aplicaron al montaje. Los HTTP 503 del 6 de septiembre siguen siendo evidencia histórica. |
| Propuesta editorial anterior 1.0.0 | `gemini-3.5-flash` en las pruebas anteriores | Llamadas satisfactorias el 6 de septiembre con frase sintética y muestra del proyecto Crear proyecto 1. Esta evidencia no valida el modelo o comportamiento selectivo nuevos. |
| Cliente común | `DEFAULT_MODEL` en `src/davinci_flow/ai/client.py` | Comparte el valor anterior; los modos históricos pueden intentar modelos alternativos. |
| Alineador y CLI históricos | Consultar sus valores en `ai/aligner.py` y `__main__.py` | Sus valores propios no quedan validados por la prueba del editor. |

El editor crea GeminiClient con `strict_model=True`: un error no cambia el modelo ni sustituye la LLM por análisis local. Aplicar una revisión guardada no hace otra llamada de IA.

## Diagnóstico de errores HTTP — 8 de septiembre de 2026

- El cliente anterior abandonaba al primer HTTP 5xx y descartaba el detalle JSON del proveedor. La configuración comprobada en el proceso de diagnóstico utiliza la clave guardada; no hay `GEMINI_API_KEY` en ese entorno. No se cambió la clave ni el modelo seleccionado. Esto no inspecciona el entorno de una instancia gráfica ya abierta.
- Ahora se realizan como máximo tres intentos por petición ante HTTP 500, 502, 503 o 504, conservando modelo y cuerpo. Las esperas son progresivas con variación aleatoria; `Retry-After` admite segundos o fecha HTTP y se acota a 30 segundos por espera. Los errores de cuota, permisos y peticiones inválidas no se reintentan automáticamente.
- Si el fallo persiste, el mensaje incluye código HTTP, modelo, número de intentos para errores 5xx y estado/motivo JSON del proveedor, con la clave oculta. No se registran prompts ni credenciales. Este diagnóstico no atribuye todos los 5xx a una única causa.
- Pruebas reales mínimas de 3.7: texto correcto en 5,31 s y JSON correcto en 2,32 s, ambas al primer intento.
- Flujo editorial real (`propose` y validación de contrato), tres subtítulos sintéticos y plantillas básicas: 3.7 devolvió tres decisiones válidas en 13,91 s tras dos intentos; 3.8 devolvió tres decisiones válidas en 11,55 s al primer intento. La recuperación de 3.7 confirma un error HTTP transitorio de los reintentables; el diagnóstico de esta ejecución contó las solicitudes, pero no conservó el código intermedio exacto. No se generó ni aplicó una revisión sobre la secuencia del usuario.
- Una medición posterior reprodujo el timeout mostrado por la interfaz: con el límite anterior de 30 s, una petición JSON mínima a 3.8 agotó el tiempo; la misma petición con 60 s respondió correctamente en 57,55 s. En la misma sesión, 3.7 respondió en 3,24 s. Otro cliente HTTP reprodujo la diferencia (3.7 correcto en 3,43 s; 3.8 agotó 20 s), por lo que no es un defecto específico de `urllib`. La ruta compatible con OpenAI respondió una vez con 3.8 en 10,55 s, pero una solicitud JSON estructurada posterior también agotó 30 s: esa ruta no demostró ser un reemplazo estable.
- El cliente concede ahora 60 s por intento y repite una vez los timeouts transitorios. Conserva estrictamente el modelo elegido. Los HTTP 5xx mantienen hasta tres intentos; 429, credenciales y errores de petición no se repiten automáticamente.
- Validación automatizada: 189 pruebas satisfactorias con `.venv/Scripts/python.exe -m unittest discover -s tests`, incluyendo recuperación de timeout, límite de intentos, conservación del modelo, ocultación de clave y ausencia de reintentos ante 429. `git diff --check` sin errores.
- Una instancia abierta necesita reiniciarse para cargar el cliente actualizado. No se verificó la interacción gráfica ni un lote completo de la secuencia del usuario.

Las peticiones editoriales envían texto de subtítulos, tiempos, contexto vecino, cortes y nombres/IDs de las plantillas seleccionadas. No envían vídeo, audio, archivos Fusion, rutas del catálogo ni la clave dentro del JSON persistido. La credencial se transmite en la cabecera de autenticación. No se afirma gratuidad, una latencia garantizada ni ausencia de retención por el proveedor.

El contrato 1.1.0 añade modo, formato, densidad, dirección creativa escrita por el usuario y nombres/categorías/IDs de hasta 80 recursos seleccionados. Los documentos se catalogan por nombre; su contenido no se lee automáticamente. El modelo compartido se persiste en `.davinci_flow/editorial_preferences.json`, separado de las credenciales. Cambiarlo afecta a propuestas nuevas, no modifica el modelo registrado en una revisión anterior.

La propuesta registra el modelo y las decisiones originales. Las revisiones manuales quedan persistidas. Evidencia y límites: `process/active/2026-09-06_fase-1_textos-llm-y-plantillas/VALIDATION.md`.
