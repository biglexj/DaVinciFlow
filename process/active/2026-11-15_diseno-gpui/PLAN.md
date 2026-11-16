# Diseño y frontend de la migración GPUI

## TAREA

Trasladar y ajustar la presentación de DaVinci Flow en GPUI respetando en gran medida su diseño, organización y flujos actuales. Trabajo delegado a un agente de frontend por petición de Biglex (2026-11-15). No se ha autorizado una reinvención visual.

## CONTEXTO

- Rama compartida: `codex/gpui-demo`.
- Diseño de referencia: implementación vigente en `src-flet/`, en especial `app/app.py`, `shared/components.py` y las vistas correspondientes. La demo actual en `src-gpui/` es el punto de partida.
- Conservar colores, Segoe UI para la interfaz, navegación lateral, nombres y prioridades de acciones, densidad de trabajo y relación entre lista/editor.
- La migración funcional continúa en [el proceso existente](../2026-11-15_demo-rust-gpui/PLAN.md); solo se crea este proceso adicional para diseño/frontend.
- El agente principal mantiene el dominio Rust, adaptadores y contratos. El agente delegado mantiene vistas, estilos y enlaces de la interfaz con ese dominio.

## FORMATO

Cambios implementados y comprobables, con evidencia breve en `VALIDATION.md`. Registrar lo preservado y los ajustes concretos; no atribuir aceptación visual de Biglex.

## RESTRICCIONES

- Respetar la implementación actual; no añadir un nuevo lenguaje visual, paletas, tipografías, paneles decorativos ni reorganizar pestañas por iniciativa propia.
- Conservar los flujos reales; no sustituir acciones funcionales por maquetas ni mostrar pestañas falsas para módulos pendientes.
- La lógica reutilizable permanece en el motor Rust. No copiar validaciones, edición, seguimiento de cambios ni exportación dentro de las vistas.
- Integrar el contrato de sesión definido en [BACKEND_CONTRACT.md](../2026-11-15_demo-rust-gpui/BACKEND_CONTRACT.md).
- Conservar todos los cambios previos del checkout. Sin publicaciones, instalación ni cambios en el ejecutable estable.

## Propiedad de archivos

Agente de frontend: `src-gpui/src/app.rs`, `src-gpui/src/app/`, `src-gpui/src/ui.rs`, `src-gpui/src/main.rs` y este proceso. Puede consultar el motor, pero no modificarlo sin coordinar.
Agente principal: `src-gpui/src/lib.rs`, módulos de dominio/adaptadores, pruebas, dependencias si hacen falta y el proceso de migración existente.
