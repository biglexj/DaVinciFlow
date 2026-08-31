# 📋 Plan de Trabajo — Animaciones Fusion, SFX en Pausas y Marcadores Cromáticos

- **Fecha de inicio**: 2026-08-31
- **Objetivo**: Desarrollar animaciones Fusion paramétricas con keyframing Bezier, detección de pausas/silencios para efectos de sonido de transición y marcadores cromáticos en línea de tiempo.
- **Responsable**: Biglex J & Antigravity

---

## 🎯 Alcance del Proceso

1. **Plantillas Fusion con Animación Paramétrica**:
   - Soporte para presets de movimiento: `pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse` y `none`.
   - Inserción de nodos `Transform` y `BezierSpline` en las composiciones `.setting` / `.comp` generadas para Resolve.
2. **Motor de SFX con Detección de Brechas / Pausas**:
   - Identificación de silencios entre subtítulos ($\ge 24$ frames) para sugerir efectos de transición (*whooshes* o *pops*).
   - Respeto estricto a las reglas de cooldown y perfiles de densidad.
3. **Estandarización de Marcadores Cromáticos**:
   - Mapeo de colores oficiales en DaVinci Resolve: Azul (Capítulos), Amarillo (Puntos Clave), Verde (SFX), Cian (Preguntas), Magenta (Correcciones IA).
4. **Documentación & Aurora Blog**:
   - Guía editorial en `docs/es/guides/flujo-de-trabajo-y-marcadores.md` lista para divulgación.
5. **Cobertura de Pruebas**:
   - Pruebas unitarias completas para los nuevos generadores de Fusion, el motor de pausas de SFX y marcadores.
