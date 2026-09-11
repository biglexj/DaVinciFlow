# Desacople de Fase de Crudo y Pestaña Dedicada «Corrección de Subtítulos» — Tareas

- Proceso: `process/active/2026-09-11_correccion-subtitulos-y-desacople-crudo/`
- Estado: `COMPLETED`

## Tareas Planificadas

### 1. Desacople y flexibilización de fases en EditorView
- [x] 1.1 Actualizar `_stage_indicator` y etiquetas para reflejar `1. Montaje y Subtítulos` en lugar de `1. Ingesta del Crudo`.
- [x] 1.2 Permitir navegación interactiva entre etapas (clic en chips de fase 1, 2 y 3).
- [x] 1.3 Incorporar creación de propuesta directa 1:1 desde subtítulos existentes al interactuar con la mesa de revisión sin forzar llamada a IA.
- [x] 1.4 Reflejar estado de montaje avanzado (cortes y subtítulos detectados) en el resumen de secuencia.

### 2. Pestaña dedicada «Corrección de subtítulos»
- [x] 2.1 Crear el módulo `src-flet/features/subtitles/subtitles_view.py` con arquitectura Flet y diseño Material 3 Expressive.
- [x] 2.2 Integrar navegación en `src-flet/app/app.py` con clave `'subtitles'`, icono `SPELLCHECK_ROUNDED` y etiqueta `Corrección`.
- [x] 2.3 Implementar lista/tabla de subtítulos con selección rápida y editor interactivo de texto.
- [x] 2.4 Implementar herramientas rápidas: Buscar y Reemplazar global, Normalizar ortografía (Unicode/signos) y Glosario.
- [x] 2.5 Implementar corrección y alineación con IA usando `ScriptAligner.align_and_correct` y detección de marcadores.
- [x] 2.6 Implementar sincronización hacia el `EditorialController` y exportación a archivo `.srt`.

### 3. Pruebas y Validación
- [x] 3.1 Ajustar índices de selectores en `tests/test_desktop.py`.
- [x] 3.2 Añadir pruebas unitarias dedicadas para `SubtitlesView` y sincronización con el controlador (`tests/test_subtitles_view.py`).
- [x] 3.3 Ejecutar suite completa de pruebas unitarias y verificar 100% verde (243/243 superadas).
- [x] 3.4 Corregir incompatibilidad de diseño en Flutter/Flet: remover `expand=True` dentro de `wrap=True` en la fila de glosario y desacoplar `expand=True` de campos en columnas no acotadas para eliminar la caja gris de error.
- [x] 3.5 Soportar clips sintéticos y generadores (como 'Color sólido', títulos o ajustes) sin offsets de medios en `capture()`, previniendo la excepción `Resolve no confirmó los offsets de un clip del montaje`.
- [x] 3.6 Implementar resiliencia y auto-reconciliación de lotes en `planner.py` (`_reconcile_batch`): auto-recuperar decisiones válidas ante omisiones, duplicaciones o índices fuera de orden por parte de la LLM en subtítulos de corta duración/caracteres especiales en el segundo intento, garantizando el contrato editorial sin abortar la propuesta completa.

### 4. Calibración Vertical de Shorts, Plantillas Media Pool (`Statement`) y Multi-Carpeta de Biblioteca
- [x] 4.1 Calibración vertical dinámica para encuadres verticales / Shorts (9:16) en `EditorialWriter`: situar títulos en el tercio inferior seguro (Y: 0.28–0.36) con interlineado compacto cohesionado según las capas activas de cada bloque.
- [x] 4.2 Ampliar escáner de plantillas Media Pool (`template_scanner.py`) para indexar títulos y macros Fusion (como `Statement`) presentes en el root/Master o carpetas del Media Pool sin restringirse exclusivamente a una carpeta llamada 'DaVinciFlow'.
- [x] 4.3 Flexibilizar `text_tool` en `writer.py` para priorizar nodos TextPlus con `StyledText` o nombrados 'Template'/'Text' sin fallar por ambigüedad cuando una macro contiene múltiples nodos TextPlus.
- [x] 4.4 Soportar múltiples carpetas por categoría en `LibraryView` y `scan_library` (separación por `;` o lista dinámica), permitiendo añadir carpetas adicionales de música/SFX/visuals sin sobrescribir las previas.
- [x] 4.5 Añadir pruebas unitarias para el nuevo posicionamiento vertical, multi-carpeta de biblioteca y escaneo flexible de plantillas Media Pool.

