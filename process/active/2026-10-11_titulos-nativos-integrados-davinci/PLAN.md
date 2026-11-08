# 2026-10-11_titulos-nativos-integrados-davinci — Plan

- Estado: `PROPOSED`
- Responsable: `biglexj`
- Fecha: `2026-10-11`

## 1. Contexto y Diagnóstico Científico

En DaVinci Resolve 21, la biblioteca de efectos (*Edit Page -> Effects -> Titles -> Fusion Titles*) cuenta con más de 130 títulos animados de fábrica (`Fade On`, `Text Box`, `Ribbon Text`, `Statement`, `Rise Fade`, `Drop In`, `Word Highlight`, `Digital Glitch`, `Simple Box 1 Line Lower Third`, etc.) junto al generador base `Text+`.

La inspección forense del sistema confirma que:
1. Todos los títulos integrados de DaVinci Resolve son en efecto archivos `.setting` de Fusion empaquetados dentro de `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Templates.drfx` (134 plantillas identificadas).
2. Cada archivo `.setting` expone una entrada `InstanceInput` con `Source = "StyledText"` sobre sus operadores internos de texto (`Text1`, `Text2_1`, `Template`, `GroupOperator` o `MacroOperator`).
3. El enfoque de herramientas externas como SnapCaptions dependía rígidamente de importar un archivo `.drb` (DaVinci Resolve Bin) en el Media Pool (`ProgramData/.../Snap Captions/Templates/For Resolve 20`), ensuciando el proyecto con bandejas y duplicados.
4. La API de DaVinci Resolve permite la inserción directa mediante `timeline.InsertFusionTitleIntoTimeline(titleName)` sin importar nada al Media Pool y sin requerir archivos intermediarios ni carriers pre-renderizados.
5. El clip resultante conserva su composición Fusion editable en tiempo real desde el Inspector de DaVinci Resolve (`StyledText`, fuentes, colores, tamaños y animaciones).

## 2. Objetivos del Plan

1. **Catálogo Integrado de Títulos Resolve**:
   - Ampliar `KineticTitleCatalog` en `src/davinci_flow/resolve/kinetic_titles.py` para incluir los títulos integrados más representativos de DaVinci Resolve (`Text+`, `Fade On`, `Text Box`, `Ribbon Text`, `Statement`, `Drop In`, `Rise Fade`, `Digital Glitch`, `Headline`, `Clean and Simple`).
   - Soportar descubrimiento automático desde `Templates.drfx` para que cualquier título nativo existente en Resolve sea seleccionable.

2. **Inserción Nativa Desacoplada del Media Pool**:
   - Robustecer `KineticTitleWriter` y `ResolveTimelineWriter` para insertar títulos nativos de Resolve llamando a `InsertFusionTitleIntoTimeline(resolve_template_name)`.
   - Localizar el operador de texto (`TextPlus`, `GroupOperator`, `MacroOperator`, `Text1`, `Text2_1`, `Template`) y configurar `StyledText` preservando la jerarquía de estilos del template.

3. **Disponibilidad en el Editor e Interfaz Flet**:
   - Conectar los títulos nativos descubiertos con la vista de Catálogo (`catalog_view.py`) y los selectores de estilo por bloque en el Editor (`editor_view.py`).
   - Ofrecer la categoría clara «✨ Nativos de DaVinci Resolve» en los filtros de plantilla.

4. **Validación y Pruebas Automatizadas**:
   - Pruebas unitarias completas simulando inserción nativa con mocks de la API de Resolve.
   - Comprobación de fallback y actualización de `StyledText`.
