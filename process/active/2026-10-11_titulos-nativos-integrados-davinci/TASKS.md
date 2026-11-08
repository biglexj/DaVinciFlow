# 2026-10-11_titulos-nativos-integrados-davinci — Tareas

- Estado: `PROPOSED`

## Tareas

- [ ] T01 — Ampliar `KineticTitleDescriptor` y `BUILTIN_KINETIC_TITLES` en `src/davinci_flow/resolve/kinetic_titles.py` con títulos nativos clave de DaVinci Resolve (`Text+`, `Fade On`, `Text Box`, `Ribbon Text`, `Rise Fade`, `Drop In`, `Digital Glitch`, `Headline`, `Clean and Simple`).
- [ ] T02 — Implementar método de auto-descubrimiento en `KineticTitleCatalog.discover_resolve_titles()` para indexar todas las plantillas `.setting` contenidas en `Templates.drfx` y carpetas de sistema.
- [ ] T03 — Optimizar `KineticTitleWriter._find_textplus_tool` y `update_fusion_text_and_style` para resolver operadores anidados de títulos nativos (`Text2_1`, `TextBox`, `RibbonText`, `GroupOperator`).
- [ ] T04 — Integrar los títulos nativos descubiertos en el catálogo de plantillas de `EditorialController` y la categoría de filtro «Nativos de DaVinci» en `catalog_view.py`.
- [ ] T05 — Añadir pruebas unitarias completas en `tests/test_kinetic_titles.py` y `tests/test_native_resolve_titles.py` verificando resolución de títulos nativos, extracción y mock de `InsertFusionTitleIntoTimeline`.
- [ ] T06 — Ejecución completa de la suite de pruebas unitarias y registro de evidencia en `VALIDATION.md`.
