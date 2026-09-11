# Desacople de Fase de Crudo y Pestaña Dedicada «Corrección de Subtítulos» — Plan

- Estado: `PROPOSED`
- Fecha: `2026-09-11`
- Proyecto: `DaVinci Flow`
- Solicitado por: `biglexj` (Audio de feedback funcional)

## 1. Contexto y Diagnóstico

El usuario probó la aplicación en un flujo de trabajo real con un vídeo recién montado y detectó dos puntos críticos de fricción:
1. **Fricción en los Pasos 1, 2 y 3 (Ligado erróneo a "Crudo"):**
   - El indicador de fases en `EditorView` marcaba fijamente `1. Ingesta del Crudo` de manera pasiva y rígida.
   - En montajes avanzados (donde ya existen cortes de edición, pistas estructuradas y subtítulos transcritos en Resolve), la aplicación seguía categorizando el proyecto como si estuviera en fase preliminar de "crudo".
   - Si no se había generado una propuesta con IA, el usuario no podía interactuar libremente con los bloques en la mesa de revisión ni cambiar de etapa.
2. **Necesidad de Enfoque en Corrección de Subtítulos (Nueva Pestaña):**
   - Durante ediciones rápidas o con poco tiempo, se pasan errores ortográficos, palabras mal transcritas o términos técnicos/nombres propios.
   - La pestaña `Editor` está sobrecargada con parámetros de estilo, dirección creativa, plantillas Fusion de 3 capas y efectos de sonido (SFX).
   - Se requiere una **nueva pestaña dedicada** (`Corrección de subtítulos` / `Corrección`) para limpiar, corregir, buscar/reemplazar y alinear textos con guion o IA sin abarrotar la vista principal de composición editorial.

## 2. Alcance de la Solución

### A. Desacople de la Fase de Crudo y Flexibilización 1-2-3 (`EditorView`)
- Renombrar el Paso 1 de `1. Ingesta del Crudo` a `1. Montaje y Subtítulos`.
- Detectar y reflejar el estado real del proyecto: si la secuencia contiene cortes de edición y subtítulos, mostrarlo claramente (`Montaje avanzado: X cortes, Y subtítulos detectados`).
- Convertir los chips de fases (1. Montaje y Subtítulos, 2. Mesa de Revisión, 3. Aplicación en Resolve) en controles interactivos navegables.
- Permitir inicio de revisión directa: si el usuario ya cuenta con subtítulos capturados y pasa a la fase 2 sin haber ejecutado la LLM, permitir generar una propuesta base 1:1 inmediata para revisar, modificar y aplicar sin dependencia forzosa de la IA.

### B. Nueva Pestaña Dedicada: «Corrección de subtítulos» (`subtitles_view.py`)
- Añadir a la barra lateral de navegación el acceso `Corrección` (`ft.Icons.SPELLCHECK_ROUNDED`) con encabezado `Corrección de subtítulos`.
- **Panel de Subtítulos**:
  - Tabla ágil con índice, intervalo de tiempo/fotogramas, texto original, texto corregido y estado.
  - Editor rápido del bloque seleccionado para modificar el texto al vuelo con botón "Guardar y siguiente".
- **Herramientas de Corrección Rápida**:
  - *Buscar y Reemplazar global*: sustitución masiva instantánea para nombres propios, marcas o palabras recurrentes.
  - *Normalizar ortografía*: corrección determinista mediante `normalize_subtitle_text` (espaciado, tildes, signos `¿?` e `¡!`).
  - *Glosario rápido*: reglas clave-valor para términos fijos.
  - *Alineación y corrección con IA (Gemini)*: integración con `ScriptAligner.align_and_correct`, con soporte opcional de guion de referencia y generación de marcadores.
- **Sincronización y Salida**:
  - *Actualizar en Editor*: propaga los subtítulos corregidos al `snapshot` activo y preserva las decisiones de la propuesta en curso.
  - *Exportar SRT*: exporta los subtítulos corregidos a formato SubRip `.srt`.
  - *Insertar Marcadores en Resolve*: inserta marcadores cromáticos en la línea de tiempo activa.

### C. Ajuste de Pruebas Automatizadas
- Corregir el selector en `test_desktop.py` afectado por los contenedores de carpetas del selector de archivos y la fila de fases.
- Añadir pruebas unitarias completas para la nueva vista de corrección y el flujo de navegación de fases desacoplado.

## 3. Criterios de Finalización

- [ ] Paso 1 renombrado y desacoplado de la etiqueta restrictiva de "crudo".
- [ ] Selector interactivo de fases (1, 2 y 3) con soporte para revisión directa de subtítulos existentes.
- [ ] Nueva pestaña `Corrección de subtítulos` operativa en la barra lateral con búsqueda/reemplazo, normalización, edición rápida y alineación IA.
- [ ] Sincronización bidireccional limpia entre la corrección de subtítulos y el editor editorial.
- [ ] Suite de pruebas automatizadas (228+ pruebas) ejecutándose al 100% en verde sin errores.
