# Modelos de IA de DaVinci Flow

- Estado: operativo
- Última actualización: 2026-08-17
- Fuente de configuración: `src/davinci_flow/ai/client.py`

Este archivo registra los modelos activos utilizados en DaVinci Flow para la alineación contextual contra guiones originales, corrección editorial de subtítulos y detección de marcadores en la línea de tiempo. No contiene claves, tokens ni valores privados.

## Registro activo

| Función | Proveedor | Identificador exacto | Estado | Verificado | Alternativa | Fuente de verdad |
|---|---|---|---|---|---|---|
| Alineación de guion, corrección de subtítulos y marcadores | Google DeepMind / Google AI | `gemini-2.5-flash` | `ACTIVE` | 2026-08-17 | `gemini-1.5-flash` | `src/davinci_flow/ai/client.py` |
| Análisis semántico avanzado / Razonamiento profundo | Google DeepMind / Google AI | `gemini-2.5-pro` | `EVALUATION` | 2026-08-17 | `gemini-2.5-flash` | `src/davinci_flow/ai/client.py` |

## Requisitos por función

### 1. Alineación de guion y corrección de subtítulos
- **Calidad esperada**: Detección de discrepancias entre el audio transcrito por DaVinci Resolve y el texto de guion, corrección de erratas, homófonos, palabras mal reconocidas y marcas registradas.
- **Latencia**: Baja (< 2.5 segundos para bloques de 100 subtítulos).
- **Coste**: Nivel gratuito / Ultra bajo consumo de tokens.
- **Modalidad y herramientas**: Salida JSON estructurada mediante `response_mime_type: "application/json"`.
- **Privacidad**: Sin persistencia de datos privados en servidores externos de terceros; peticiones directas vía HTTPS cifrado.

### 2. Detección de marcadores en línea de tiempo
- **Calidad esperada**: Identificación de momentos de énfasis, inicio de capítulos, menciones de marcas y conclusiones.
- **Salida**: Asignación de colores estándar de DaVinci Resolve (`Cyan`, `Yellow`, `Pink`, `Green`, `Purple`) con notas explicativas.

## Comprobación

- Validado mediante suite de pruebas unitarias simuladas en `tests/test_gemini_client.py` y `tests/test_script_aligner.py`.
- Enlazado con el proceso activo `process/active/2026-08-17_integracion-gemini-guion-y-marcadores/`.

## Historial de cambios

- **2026-08-17**: Incorporación inicial de `gemini-2.5-flash` para alineación de guion, corrección de subtítulos y marcadores automáticos en DaVinci Resolve.
