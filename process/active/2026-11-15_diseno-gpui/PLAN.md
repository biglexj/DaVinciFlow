# Migración completa del diseño a GPUI

> Alcance vigente, 2026-11-17: Biglex asigna al agente principal la continuación completa, incluido el diseño. Se conserva el sidebar; se reducen espaciado, tarjetas vacías y expansión innecesaria. Estado actual por pestaña: `src-gpui/README.md`. El proceso permanece activo hasta completar paridad y aceptación visual.

## TAREA

Migrar **todo el diseño y frontend** de DaVinci Flow desde Flet a Rust + GPUI, pestaña por pestaña, conservando en gran medida la identidad, distribución, textos y flujos actuales.

Biglex asignó la ejecución a la sesión del agente principal el 2026-11-15 («tomalo y ejecuta»), tras la corrección de alcance que reservaba la migración completa para otra agencia. El agente principal conserva además el backend/motor, sus adaptadores y contratos; la separación por áreas se mantiene en la práctica: las vistas no duplican reglas del motor.

La integración parcial anterior es un antecedente, no la aprobación de la migración completa del diseño.

## CONTEXTO

- Rama: `GPUI`. Revisar el checkout y preservar cambios ajenos antes de editar.
- Referencia visual y funcional: `src-flet/app/app.py`, `src-flet/app/views.py`, `src-flet/shared/` y todas las vistas de `src-flet/features/`.
- Base nativa: `src-gpui/` con las 11 pestañas conectadas.
- Conservar paleta, tipografías por rol, navegación lateral, nombres, prioridades de acciones, densidad y distribución. Primero trasladar; los retoques se revisarán después con Biglex.
- El motor y su avance pertenecen al [proceso de migración](../2026-11-15_migracion-rust-gpui/PLAN.md). Consultar [BACKEND_CONTRACT.md](../2026-11-15_migracion-rust-gpui/BACKEND_CONTRACT.md) y coordinar los contratos faltantes.

## ALCANCE

La agencia debe inventariar y trasladar la ventana base, navegación, componentes compartidos y todas las áreas existentes:

| Área | Referencia Flet |
|---|---|
| Asistente IA | `features/assistant/assistant_view.py` |
| Editor | `features/editor/editor_view.py` |
| Corrección | `features/subtitles/subtitles_view.py` |
| Generación de voz | `features/voice/voice_view.py` |
| B-Rolls | `features/brolls/brolls_view.py` |
| Música | `features/library/library_view.py`, variante `music` |
| Efectos (SFX) | `features/sfx/sfx_view.py` |
| Plantillas | `features/catalog/catalog_view.py` |
| Luna Fetch | `features/luna_fetch/fetch_view.py` |
| Biblioteca | `features/library/library_view.py` |
| Ajustes | `features/settings/settings_view.py` |
| Actualizaciones | `features/about/update_panel.py` |
| Acerca de | `features/about/about_dialog.py` |

También incluye selectores, diálogos, formularios, tablas/listas, estados vacíos, progreso, errores, accesibilidad, previsualizadores multimedia y enlaces de interacción al backend. Comprobar el estado real de cada función: una vista presente no demuestra que su servicio esté habilitado.

## FORMATO

- Trabajar por incrementos revisables y actualizar `TASKS.md` y `VALIDATION.md`.
- Por área: registrar referencia, elementos conservados, acciones conectadas y diferencias o dependencias pendientes.
- Comprobar compilación y flujos afectados según el tamaño del cambio. Distinguir verificación técnica, prueba real y aceptación visual de Biglex.

## RESTRICCIONES

- Respetar el diseño actual. No introducir otra identidad visual ni reorganizar los flujos sin indicación de Biglex.
- El backend mantiene reglas, validaciones, edición, persistencia, IA y comunicación con Resolve. La agencia consume sus contratos; no duplica esa lógica dentro de las vistas.
- Si falta un contrato, documentar la necesidad y coordinarla con el backend. No fingir conexiones, resultados ni éxitos para dar por terminada una pestaña.
- Las vistas aún incompletas se identifican como tales; no exponer controles que aparenten funcionar ni declarar paridad por tener solo el aspecto visual.
- Preservar originales, datos, credenciales, sesiones y cambios del usuario. No sustituir la instalación estable, publicar ni cambiar la versión como parte del traslado visual.

## PROPIEDAD

- **Frontend de esta sesión:** `src-gpui/src/app.rs`, `src-gpui/src/app/`, `src-gpui/src/ui.rs`, `src-gpui/src/main.rs`, recursos visuales derivados necesarios y este proceso.
- **Motor y adaptadores:** `src-gpui/src/lib.rs`, módulos de dominio, pruebas y el proceso de migración existente. Los cambios de dominio de este incremento (glosario y restauración de un bloque) se registran en el proceso de migración.

## ENTREGA

El alcance se completa cuando todas las áreas estén contrastadas con Flet, las acciones disponibles estén conectadas a contratos reales y los límites pendientes queden explícitos. La aceptación visual corresponde a Biglex. El estado actual de cada área figura en `TASKS.md` y la evidencia en `VALIDATION.md`.
