# 🔬 Validación — Animaciones Fusion, SFX en Pausas y Marcadores Cromáticos

Registro de pruebas y evidencias técnicas.

## 🧪 Pruebas Automatizadas
- [x] Pruebas unitarias de generación de plantillas Fusion con keyframing Bezier (`test_fusion_template.py`).
- [x] Pruebas unitarias del motor de SFX con detección de silencios/gaps entre bloques (`test_sfx_engine.py`).
- [x] Pruebas de integración de pipeline (planificación y escritura de timeline con animaciones y SFX en `test_timeline_writer.py`).

## 📊 Resultados de Verificación
- Total de pruebas unitarias ejecutadas: **101 pruebas**.
- Resultado: **101/101 en verde (0 fallos, 0 errores)**.
- Tiempo de ejecución: **0.358 segundos**.
- Verificación sintáctica:
  - Generación de `.setting` válida con nodos `TextPlus`, `Transform`, `BezierSpline` y `MediaOut`.
  - Disparo de SFX de transición cuando la brecha temporal entre subtítulos supera los 24 fotogramas (1.0 s a 24 fps).
  - Mapeo de marcadores cromáticos estandarizados: Azul (Capítulos), Amarillo (Puntos Clave), Verde (SFX), Cian (Preguntas), Magenta (Glosario / Corrección IA).
