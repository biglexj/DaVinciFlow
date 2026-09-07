# Modelos de IA de DaVinci Flow

Última actualización: 2026-09-06. Los identificadores de este registro describen el código local y las llamadas observadas; no garantizan disponibilidad futura del proveedor.

| Función | Modelo configurado | Evidencia |
|---|---|---|
| Propuesta editorial revisable | `gemini-3.5-flash`, editable en el campo Modelo exacto | Llamadas reales satisfactorias el 6 de septiembre: frase sintética, primeros dos subtítulos y muestra del proyecto Crear proyecto 1. Un intento inicial devolvió HTTP 503. |
| Cliente común | `DEFAULT_MODEL` en `src/davinci_flow/ai/client.py` | Comparte el valor anterior; los modos históricos pueden intentar modelos alternativos. |
| Alineador y CLI históricos | Consultar sus valores en `ai/aligner.py` y `__main__.py` | Sus valores propios no quedan validados por la prueba del editor. |

El editor crea GeminiClient con `strict_model=True`: un error no cambia el modelo ni sustituye la LLM por análisis local. Aplicar una revisión guardada no hace otra llamada de IA.

Las peticiones editoriales envían texto de subtítulos, tiempos, contexto vecino, cortes y nombres/IDs de las plantillas seleccionadas. No envían vídeo, audio, archivos Fusion, rutas del catálogo ni la clave dentro del JSON persistido. La credencial se transmite en la cabecera de autenticación. No se afirma gratuidad, una latencia garantizada ni ausencia de retención por el proveedor.

La propuesta registra el modelo y las decisiones originales. Las revisiones manuales quedan persistidas. Evidencia y límites: `process/active/2026-09-06_fase-1_textos-llm-y-plantillas/VALIDATION.md`.
