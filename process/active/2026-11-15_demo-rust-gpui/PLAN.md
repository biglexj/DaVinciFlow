# Demo incremental Rust + GPUI

Autorización: Biglex pidió una rama nueva y una demo funcional, migrando por pestañas y bases (2026-11-15).
Rama: `codex/gpui-demo`. La rama se creó desde `main`; los cambios previos del checkout permanecen intactos y no pertenecen a esta tarea.

## Primer incremento

- Aplicación independiente en `src-gpui/`, sin sustituir Flet ni modificar la instalación estable.
- Base nativa: ventana, tema actual, navegación, estados de error y operaciones fuera del hilo de interfaz.
- Corrección: importar SRT real, listado virtualizado, edición, búsqueda/reemplazo, normalización Unicode, restauración y exportación UTF-8.
- Biblioteca: inventario nativo de una carpeta elegida, filtros y apertura de ubicación. Sin declarar reproducción multimedia.
- Resolve: lectura explícita de estado y subtítulos por un adaptador Python pequeño que reutiliza el transporte actual; sin escritura en la secuencia.
- Documentar capacidades pendientes por pestaña. No declarar paridad completa, rendimiento ganado, aceptación visual ni publicación.

## Estrategia

### Reparto autorizado el 2026-11-15

Biglex asigna al agente principal la lógica/backend y delega diseño/frontend respetando en gran medida la interfaz actual. El único proceso adicional es [Diseño GPUI](../2026-11-15_diseno-gpui/PLAN.md). Este proceso conserva la migración del motor y su [contrato de sesión](BACKEND_CONTRACT.md).

Segundo incremento: extraer del estado GPUI el ciclo de edición de subtítulos, validar cambios pendientes, mantener un historial de texto y registrar exportaciones por estado inmutable. La interfaz consume el motor sin duplicar sus reglas.

Portar el dominio que no requiere Resolve a Rust. Mantener su adaptador de scripting y MCP en Python al inicio. La interfaz consume resultados tipados y comunica errores reales; no crea datos de ejemplo para simular éxito.
GPUI Kit se fija a 0.9.1 para disponer de controles de edición, foco y accesibilidad sobre su snapshot GPUI compatible.

## Criterios de entrega

Compilar y ejecutar en Windows; comprobar importación, edición y exportación reales; pruebas del dominio y errores; registrar el resultado de la consulta real a Resolve según su disponibilidad. Mantener el proceso activo para la migración posterior.
