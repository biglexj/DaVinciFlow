# Modelos de IA de DaVinci Flow

Última actualización: 2026-09-07. Los identificadores de este registro describen el código local y las llamadas observadas; no garantizan disponibilidad futura del proveedor.

| Función | Modelo configurado | Evidencia |
|---|---|---|
| Propuesta editorial selectiva 1.1.0 | Modelo compartido desde Ajustes; preferencia del usuario `gemini-3.8-flash` | Dos llamadas reales devolvieron HTTP 503 durante el trabajo del 6 de septiembre. Sin propuesta selectiva válida ni cambio silencioso de modelo. Pendiente de revalidar disponibilidad. |
| Propuesta editorial anterior 1.0.0 | `gemini-3.5-flash` en las pruebas anteriores | Llamadas satisfactorias el 6 de septiembre con frase sintética y muestra del proyecto Crear proyecto 1. Esta evidencia no valida el modelo o comportamiento selectivo nuevos. |
| Cliente común | `DEFAULT_MODEL` en `src/davinci_flow/ai/client.py` | Comparte el valor anterior; los modos históricos pueden intentar modelos alternativos. |
| Alineador y CLI históricos | Consultar sus valores en `ai/aligner.py` y `__main__.py` | Sus valores propios no quedan validados por la prueba del editor. |

El editor crea GeminiClient con `strict_model=True`: un error no cambia el modelo ni sustituye la LLM por análisis local. Aplicar una revisión guardada no hace otra llamada de IA.

Las peticiones editoriales envían texto de subtítulos, tiempos, contexto vecino, cortes y nombres/IDs de las plantillas seleccionadas. No envían vídeo, audio, archivos Fusion, rutas del catálogo ni la clave dentro del JSON persistido. La credencial se transmite en la cabecera de autenticación. No se afirma gratuidad, una latencia garantizada ni ausencia de retención por el proveedor.

El contrato 1.1.0 añade modo, formato, densidad, dirección creativa escrita por el usuario y nombres/categorías/IDs de hasta 80 recursos seleccionados. Los documentos se catalogan por nombre; su contenido no se lee automáticamente. El modelo compartido se persiste en `.davinci_flow/editorial_preferences.json`, separado de las credenciales. Cambiarlo afecta a propuestas nuevas, no modifica el modelo registrado en una revisión anterior.

La propuesta registra el modelo y las decisiones originales. Las revisiones manuales quedan persistidas. Evidencia y límites: `process/active/2026-09-06_fase-1_textos-llm-y-plantillas/VALIDATION.md`.
