# Entrega para fase 2

Implementación y muestra técnica real comprobadas en Resolve Studio 21.0.0b.33. Biglex autorizó las pruebas en vivo. La copia DF — Prueba fase 1 — 2026-09-06 contiene 27 clips; falta aceptación visual del usuario. Ver LIVE_VALIDATION.md.

## Contratos que se deben reutilizar

- `editorial/model.py`: Snapshot, Template, Decision y Proposal; versión editorial `1.0.0`. Conserva identidad, rango, FPS, origen, subtítulos y huella del montaje.
- `editorial/planner.py`: `propose(snapshot, templates, client)`, LLM por lotes con contexto vecino y validación estricta. No escribe ni añade SFX.
- `Proposal.edit(...)` invalida revisión salvo `reviewed=True`; cambiar texto exige motivo. `save/load` conserva la revisión.
- `Proposal.generation_plan()` adapta al GenerationPlan histórico sin cambiar su esquema. El ID incluye la revisión editorial, no solo el texto de origen.
- `editorial/service.py`: `apply_reviewed(proposal, session, record_path)` y `undo_reviewed(session, record_path)`. Reciben una sesión explícita y no llaman a la IA.
- `editorial/writer.py`: tres pistas de texto, comprobación exacta de posición/duración/texto, archivos instalados y copias del Media Pool.
- `ui/editorial_window.py`: editor compartido mediante `--editorial-ui` y accesos desde las interfaces anteriores.

## Integración de sonido

Extender explícitamente contrato y versión para sonido revisable y persistido. Incluir recursos, tiempos, ganancia y fundidos en la identidad de revisión. No inferir otra propuesta durante Aplicar.

El escritor de fase 1 crea solo tres pistas de texto y exige deshacer la muestra antes de aplicar una revisión distinta. Fase 2 completa dos pistas sonoras y regeneración selectiva, conservando registros y clips ajenos. No sustituir el recorrido por `generate_from_active_timeline`, que mantiene la generación histórica con reanálisis.

## Pendientes concretos

Aceptación visual de Biglex, ajuste de legibilidad y duración de animaciones según plantilla; no existe compatibilidad universal certificada. Las seis composiciones del Media Pool admiten edición sin alterar originales. Rise Fade y Text+ básico Principal tienen comprobación visual.

No reintroducir portadores PNG: provocaban duraciones excesivas y desplazamiento del siguiente título. En la versión probada endFrame es exclusivo; verificar siempre posición y duración reales. Las macros instaladas pueden usar Outputs sin ordered() y necesitan conexión explícita de su salida de imagen después de importar.

El registro de la UI usa record_path_for(project_id, timeline_id), separado por secuencia. Los básicos incluidos se distribuyen como datos del paquete. No cambiar Proposal 1.0.0 de forma silenciosa al añadir sonido.

