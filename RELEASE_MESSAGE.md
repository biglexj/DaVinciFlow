# 🎬 ¡Presentamos DaVinci Flow v0.1.0 (Beta Experimental)!

Nos complace anunciar el primer lanzamiento público de **DaVinci Flow v0.1.0**, la nueva herramienta del ecosistema Biglex diseñada para acelerar y potenciar la edición de video en **DaVinci Resolve 21** mediante automatización inteligente y flujos de trabajo asistidos por IA.

---

### ✨ ¿Qué es DaVinci Flow?
**DaVinci Flow** transforma la tediosa tarea de crear subtítulos dinámicos y organizar la línea de tiempo en un proceso automatizado, limpio y creativo. Analiza las pistas de subtítulos transcritas por DaVinci Resolve (o archivos `.srt` externos) y las convierte en subtítulos multicapa modernos listos para YouTube, Shorts, TikTok y producciones de alta calidad.

---

### 🚀 Novedades Principales

1. **🎭 Subtítulos Dinámicos Multicapa**:
   - Clasificación inteligente de palabras en capas de **Contexto**, **Principal**, **Acento** y **Efectos SFX**.
   - Generación no destructiva en pistas de video independientes (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`).

2. **📄 Alineación de Guion & Corrección con Gemini IA**:
   - ¿DaVinci Resolve transcribió mal una palabra, un nombre de marca o una jerga local? Pega tu guion original y DaVinci Flow comparará el texto, corrigiendo las palabras erróneas manteniendo los fotogramas y la sincronización labial exacta.
   - Glosario personalizado de reemplazos fijos de marcas y tecnicismos.

3. **🎯 Marcadores Automáticos en la Línea de Tiempo**:
   - Detección asistida por IA de temas clave, momentos de clímax y cambios de ritmo, insertando marcadores de colores con notas descriptivas directamente en tu timeline.

4. **⚡ Lector Híbrido (Resolve Timeline & Archivos SRT)**:
   - Capacidad de leer directamente la pista activa de Resolve o cargar cualquier archivo `.srt` exportado.

5. **🎨 Interfaz Gráfica Nativa DaVinci**:
   - Ventana flotante compacta, sobria y ergonómica diseñada con la paleta de color neutral de DaVinci Resolve (`#202020`), posicionada para no obstruir el visor de video.

---

### 📦 Instalación Rápida

1. Instala el lanzador en DaVinci Resolve ejecutando en tu terminal:
   ```bash
   uv run davinci-flow --install
   ```
2. Abre **DaVinci Resolve**.
3. En el menú superior, ve a: **Espacio de trabajo -> Scripts -> DaVinci Flow**.

---

### 🌐 Ecosistema & Donaciones
- **Launchpad Web**: [https://biglexj.com/desarrollo](https://biglexj.com/desarrollo)
- **Apoya el Desarrollo**: [https://biglexj.com/donaciones](https://biglexj.com/donaciones)
- **Código y Comunidad**: MIT License • Biglex J (2026)
