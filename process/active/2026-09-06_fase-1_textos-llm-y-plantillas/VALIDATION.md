# Fase 1 — Validación

Estado: recorrido técnico real comprobado; aceptación visual pendiente.

## Evidencia

- Windows, Python 3.13 y Resolve Studio 21.0.0b.33; prueba del 6 de septiembre de 2026.
- 154 pruebas unitarias/de integración simulada correctas, incluida UI sin conexión. Comando: .venv/Scripts/python.exe -m unittest discover -s tests -q.
- Paquete wheel construido con uv build; se verificó que incluye las tres plantillas básicas.
- LLM real gemini-3.5-flash: llamadas sobre frase sintética y subtítulos del proyecto. Un HTTP 503 inicial no cambió de modelo.
- Seis plantillas nativas comprobadas por copia, texto y preservación de originales. Rise Fade instalado y Text+ básico Principal verificados en el visor.
- Muestra final de 16 subtítulos, uno excluido por durar dos fotogramas: 27 clips en tres pistas. Reaplicación conserva identidades; reversión elimina solo la muestra. Original Timeline 1 conservado.
- Botón principal, captura, carga de propuesta y aplicación comprobados mediante la interfaz real.
- Informe detallado: [LIVE_VALIDATION.md](LIVE_VALIDATION.md), [MEDIA_POOL_VALIDATION.json](MEDIA_POOL_VALIDATION.json) y [SAMPLE_EXECUTION.json](SAMPLE_EXECUTION.json).

## Comprobaciones

- [x] V01 técnico — Ambas fuentes insertan texto y duración correctos; nodos originales conservados. La adaptación estética de animaciones queda dentro de V07.
- [x] V02 — Propuesta preserva palabras, negación, tildes y número 2024. Revisión manual de capas persistida. No se corrigen automáticamente errores de transcripción.
- [x] V03 — Contratos inválidos, archivos cambiados, timeout y modelo no disponible se rechazan sin modo local silencioso. Pruebas automatizadas; no se provocaron fallos del proveedor de forma artificial.
- [x] V04 — Propuesta LLM real, revisión y aplicación real en Resolve.
- [x] V05 — Edición anterior a aplicar, reaplicación sin duplicados y reversión por registro.
- [x] V06 — Fuente desactualizada rechazada antes de escribir; cobertura automatizada y comparación contra sesión real.
- [ ] V07 — Aceptación de Biglex durante reproducción: legibilidad, tamaño, superposición y entradas/salidas según cada plantilla.

## Límites

El inventario no certifica todos los títulos. Una frase larga desbordó Rise Fade y se sustituyó por una frase breve en la muestra. Los keyframes fijos no se retiman automáticamente. Los subtítulos nativos permanecen visibles y el audio previo no se modifica. Las dos pistas de sonido y la regeneración selectiva se completan en fase 2.

La autorización inicial de mantener Resolve cerrado fue sustituida por la autorización explícita posterior para pruebas en vivo. Se trabajó en una copia de la secuencia.
