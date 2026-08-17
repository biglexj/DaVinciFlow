# Integración de Gemini, Comparación con Guion Original, Corrección de Jergas/Marcas y Marcadores en Línea de Tiempo — Validación

- Estado: `VERIFIED`

## Comprobaciones

- [x] V01 — Agente — Ejecutar suite completa de pruebas unitarias (`uv run python -m unittest discover -s tests`). Esperado: 100% de tests pasando sin errores. Resultado: 82/82 pruebas aprobadas en 0.074s.
- [x] V02 — Agente — Comprobar cliente Gemini con mock de respuestas y manejo de errores de red/cuota/claves inválidas. Esperado: excepciones controladas de DaVinciFlowError sin filtrar secretos. Resultado: validado en `tests/test_gemini_client.py`.
- [x] V03 — Agente — Comprobar alineación de subtítulos con guion original y reemplazo de marcas ("biglex" -> "Biglex J"). Esperado: texto corregido con timecodes intactos y lógica anti-duplicación. Resultado: validado en `tests/test_script_aligner.py`.
- [x] V04 — Agente — Comprobar inserción de marcadores con ResolveMarkerWriter en timeline mockeada y cálculo de frames. Esperado: marcadores insertados con nombres, notas y colores correctos. Resultado: validado en `tests/test_marker_writer.py`.
- [x] V05 — Agente — Comprobar CLI con parámetros `--script`, `--glossary`, `--correct-ai` y `--add-markers`. Esperado: ejecución fluida en modo plan, corrección y simulación. Resultado: validado en `tests/test_main_cli.py`.
- [ ] V06 — Tester / Usuario — Probar interfaz gráfica en DaVinci Resolve con guion y clave API de Gemini. Esperado: corrección asistida y marcadores automáticos en la línea de tiempo.

## Registro de fallos

- Sin fallos pendientes.
