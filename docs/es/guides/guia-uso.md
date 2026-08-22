# 📖 Guía de Uso — DaVinci Flow

Guía práctica para creadores y editores de contenido sobre el uso de **DaVinci Flow** en **DaVinci Resolve 21**.

---

## 1. Instalación y Apertura

1. En la terminal de tu proyecto, instala el lanzador de DaVinci Resolve:
   ```bash
   uv run davinci-flow --install
   ```
2. Abre tu proyecto en **DaVinci Resolve 21**.
3. En la barra de menú superior, selecciona:
   **Espacio de trabajo** ➔ **Scripts** ➔ **DaVinci Flow**.
4. La ventana flotante de DaVinci Flow se abrirá en el lateral derecho de la pantalla con la paleta de color neutral de Resolve.

---

## 2. Flujo de Trabajo con Subtítulos y Guion

### Paso 1: Selección de Origen de Subtítulos
- **Opción A (Línea de tiempo de Resolve)**: Si ya utilizaste la función nativa de DaVinci *Crear subtítulos a partir de audio*, selecciona el número de pista (ej. `1`) y pulsa **🎬 Leer Pista**.
- **Opción B (Archivo externo .SRT)**: Pulsa **📂 Cargar SRT** para seleccionar un archivo `.srt` exportado desde otra herramienta.

### Paso 2: Configuración de Gemini IA & Glosario
1. **API Key**: Ingresa tu clave de Google Gemini y pulsa **💾 Guardar** (se guarda de forma cifrada/segura localmente o se puede usar la variable `GEMINI_API_KEY`).
2. **Glosario / Marcas**: Si tu video contiene jergas locales, nombres de marcas o tecnicismos que Resolve suele confundir, añade pares de reemplazo separados por comas:
   ```text
   biglex: Biglex J, resolve: DaVinci Resolve, premiere: DaVinci
   ```
3. **Guion Original**: Pulsa **📄 Cargar Guion .txt** o pega directamente el texto original de tu guion en el área de texto.

### Paso 3: Análisis y Previsualización
- Pulsa **🔍 Analizar Capas** para que DaVinci Flow procese el texto y clasifique las capas:
  - **Contexto**: Subordinadas y preparación visual.
  - **Principal**: Núcleo del mensaje.
  - **Acento**: Palabras clave destacadas.
  - **SFX**: Efectos de sonido sugeridos.
- Si activas **✨ Corregir con Guion**, la IA comparará la transcripción contra tu guion, corrigiendo errores ortográficos y manteniendo la sincronización exacta.

### Paso 4: Generación en Línea de Tiempo
- Pulsa **⚡ Generar en Timeline**. DaVinci Flow creará las capas correspondientes en pistas independientes de video (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) e insertará los marcadores temáticos con colores en tu línea de tiempo.
- **¿Quieres deshacer?**: Pulsa **🔄 Deshacer** para eliminar de golpe todos los elementos generados sin alterar tu proyecto base.
