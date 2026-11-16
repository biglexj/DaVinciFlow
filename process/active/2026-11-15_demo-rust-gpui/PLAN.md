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

Portar el dominio que no requiere Resolve a Rust. Mantener su adaptador de scripting y MCP en Python al inicio. La interfaz consume resultados tipados y comunica errores reales; no crea datos de ejemplo para simular éxito.
GPUI Kit se fija a 0.9.1 para disponer de controles de edición, foco y accesibilidad sobre su snapshot GPUI compatible.

## Criterios de entrega

Compilar y ejecutar en Windows; comprobar importación, edición y exportación reales; pruebas del dominio y errores; registrar el resultado de la consulta real a Resolve según su disponibilidad. Mantener el proceso activo para la migración posterior.
