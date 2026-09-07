# 🔬 Validación — Asistente Contextual de B-Rolls y Assets de Sonido

Registro de pruebas y evidencias técnicas.

## 🧪 Pruebas Automatizadas
- [x] Pruebas del catálogo y escáner de B-Rolls (`test_broll_catalog.py`): Cobertura de extracción de tags, cálculo de score y escaneo de directorio.
- [x] Pruebas del emparejador semántico (`test_broll_matcher.py`): Cobertura de asignación heurística y asistida por Gemini AI.
- [x] Pruebas de inserción en Resolve (`test_timeline_writer.py`): Cobertura de inserción en pista `DF_BROLL` y verificación de items aplicados.

## 📊 Resultados de Verificación
- **116 de 116 pruebas automatizadas ejecutadas y superadas en 0.487s**.
- Interfaz gráfica actualizada con selector de carpeta de recursos, checkbox de B-Rolls y columna `B-Roll / SFX` en la tabla de previsualización.

