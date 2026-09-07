# 🎬 ¡Lanzamiento de DaVinci Flow v0.2.0!

Nos complace presentar **DaVinci Flow v0.2.0**, una importante evolución diseñada para transformar el ritmo audiovisual, la tipografía y la postproducción en **DaVinci Resolve 21** con flujos editoriales impulsados por IA y generación procedural.

---

### ✨ ¿Qué hay de nuevo en la v0.2.0?
**DaVinci Flow v0.2.0** expande las capacidades del flujo de trabajo multicapa, integrando un editor de decisiones tipográficas asistido por Google Gemini, animaciones Fusion avanzadas, efectos sonoros automáticos en pausas y gestión inteligente de B-Rolls.

---

### 🚀 Novedades Destacadas

1. **🧠 Editor Editorial con Gemini IA & Énfasis Selectivo**:
   - Análisis contextual que distribuye textos en tres capas complementarias (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) o deja silencios visuales estratégicos para potenciar el mensaje.
   - Modo de trabajo híbrido: compatible tanto con sesiones directas en DaVinci Resolve como con previsualización sin conexión mediante archivos SRT.

2. **✨ Animaciones Fusion Paramétricas**:
   - Soporte integral de composiciones `.setting`, `.comp` y paquetes `.drfx` del sistema o del Media Pool.
   - Curvas de interpolación Bézier nativas: `pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse` y `typewriter`.

3. **🔊 Efectos de Sonido (SFX) Procedurales en Silencios**:
   - Detección automática de pausas temporales entre subtítulos para insertar acentos sonoros en la pista `DF_SFX`.
   - 8 efectos procedurales generados en tiempo real sin dependencias pesadas (*whoosh*, *pop*, *bell*, *click*, *riser*, *glitch*, *thud*, *chime*).

4. **🎞️ Asistente Contextual de B-Rolls**:
   - Catalogador recursivo de recursos multimedia con emparejamiento semántico para sugerir e insertar clips de apoyo en la pista `DF_BROLL`.

5. **🎯 Marcadores Cromáticos Estandarizados**:
   - Organización visual de la línea de tiempo con colores universales (Capítulos, Claves, SFX, Preguntas, Correcciones y CTA) y reversión atómica limpia.

---

### 📦 Instalación y Uso Rápido

1. Instala el lanzador en DaVinci Resolve desde tu terminal:
   ```bash
   uv run davinci-flow --install
   ```
2. Abre el nuevo Editor Editorial sin conexión:
   ```bash
   uv run davinci-flow --editorial-ui
   ```
3. O en **DaVinci Resolve**, accede desde el menú superior:
   **Espacio de trabajo -> Scripts -> DaVinci Flow**.

---

### 🌐 Ecosistema & Donaciones
- **Launchpad Web**: [https://biglexj.com/desarrollo](https://biglexj.com/desarrollo)
- **Apoya el Desarrollo**: [https://biglexj.com/donaciones](https://biglexj.com/donaciones)
- **Código y Comunidad**: MIT License • Biglex J (2026)
