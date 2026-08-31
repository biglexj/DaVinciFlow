# 🎬 Release Notes — DaVinci Flow

> [!IMPORTANT]
> **Protocolo de Verificación de Versión en GitHub ("Lanzar actualización") [CRÍTICO]:**
> - Al recibir la orden de *"Lanzar actualización"*, es **OBLIGATORIO Y DE LEY** consultar primero la última versión publicada en GitHub / remoto (`gh release list` o `git ls-remote --tags`).
> - Si la versión local ya fue subida (así haya sido lanzada hace minutos), NUNCA se debe sobrescribir ni re-etiquetar. Se DEBE incrementar obligatoriamente a la siguiente versión de parche (e.g. `0.1.0` → `0.1.1`).
>
> **Sanitización de Notas (CRÍTICO):**
> - Los mensajes de las notas de lanzamiento DEBEN estar limpios de rutas de archivos del sistema local (ej. `d:\Proyectos\...`), nombres de variables internas, fragmentos de prompts o logs técnicos de depuración. Deben redactarse con lenguaje limpio, profesional y enfocado al usuario final.
>
> **Estándar SemVer Flexible (Core-Docs v1.7.0):**
> - Se utiliza SemVer estándar (`MAJOR.MINOR.PATCH`) sin límites artificiales por dígito (segmentos mayores a 9 como `0.1.12` son 100% válidos).
> - Se incrementa `PATCH`, `MINOR` o `MAJOR` según el alcance real del cambio y compatibilidad, sin saltos forzados de versión basados únicamente en alcanzar un dígito 9.
> - **Extensión proporcional en Release Notes:** La cantidad de párrafos depende del alcance: 1 para un hito pequeño, 2 cuando hay dos cambios relevantes, 3 como extensión habitual, 4 para hitos relativamente grandes y hasta 5 para lanzamientos de gran alcance. Cada párrafo debe concentrarse en un cambio principal y evitar descripciones excesivamente largas o listas detalladas de archivos.

Registro histórico de cambios y versiones de **DaVinci Flow**.

---

## [0.1.0] - 2026-08-21

### Resumen
Lanzamiento inaugural de **DaVinci Flow v0.1.0 (Experimental)**, la suite de automatización para **DaVinci Resolve 21** diseñada para revolucionar el flujo de postproducción audiovisual mediante la generación de **Subtítulos Dinámicos Multicapa** (Contexto, Principal, Acento y Efectos SFX), lectura híbrida de pistas nativas de Resolve y archivos `.SRT`, motor inteligente de **Alineación con Guion Original mediante la API de Google Gemini**, corrección automática de transcripciones imperfectas, glosario de jergas y nombres de marca con lógica anti-duplicación, e inserción automática de **Marcadores Temáticos** en la línea de tiempo.

### Detalles
- **Generación de Subtítulos Dinámicos Multicapa**: Sistema de análisis sintáctico y semántico que clasifica automáticamente los textos en capas diferenciadas de *Contexto* (preparación y subordinadas), *Principal* (mensaje central y narración base), *Acento* (palabras de alto impacto, cifras o énfasis emocional) y propuestas de *Efectos SFX* para acentuar el dinamismo visual en pistas no destructivas (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`, `DF_SFX`).
- **Lector Híbrido Resiliente (Línea de Tiempo & Archivos SRT)**: Adaptador de lectura avanzada que extrae con precisión fotogramas, nombres y textos de clips de subtítulos nativos en Resolve 21, complementado con un parser integrado de archivos SubRip (`.srt`) para procesar guiones exportados desde herramientas externas o transcripciones por lotes sin restricciones.
- **Alineación con Guion Original y Asistente IA con Gemini**: Motor de sincronización que compara la transcripción fonética imperfecta generada por Resolve contra el texto del guion original del creador. Corrige errores ortográficos, confusiones de palabras y aplica un glosario configurable de marcas y jergas, garantizando el respeto estricto de los códigos de tiempo y fotogramas originales.
- **Inserción Automatizada de Marcadores en Línea de Tiempo**: Detección asistida por IA de puntos de inflexión, cambios de tema, ganchos de atención (*hooks*) y momentos destacados del guion, insertando automáticamente marcadores de colores con nombres descriptivos y notas en la línea de tiempo activa de DaVinci Resolve.
- **Interfaz Gráfica Nativa de Resolve (UIManager) y Fallback Tkinter**: Ventana gráfica no bloqueante acoplada en el cuadrante derecho del espacio de trabajo con paleta gris neutra (`#202020`), simetría visual impecable, previsualización en árbol de bloques clasificados y soporte multiplataforma independiente.
- **CLI Completa, Modo Simulación (Dry-Run) e Idempotencia**: Interfaz de línea de comandos exhaustiva (`davinci-flow`) con modos de inspección, planificación, generación, deshecho atómico (`--revert`) y validación previa en modo simulación para verificar cambios sin alterar la línea de tiempo.
