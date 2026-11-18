# Demo incremental Rust + GPUI

Autorización: Biglex pidió una rama nueva y una demo funcional, migrando por pestañas y bases (2026-11-15).
Rama: `codex/gpui-demo`. La rama se creó desde `main`; los cambios previos del checkout permanecen intactos y no pertenecen a esta tarea.

## Primer incremento

### Alcance vigente: continuación del 2026-11-17

Biglex pide continuar toda la migración, incluido el diseño. Esta instrucción sustituye la separación de responsabilidades descrita más abajo como antecedente del 15 de noviembre. El agente principal asume lógica y presentación, conserva el sidebar y compacta las áreas de trabajo con criterio propio.

El incremento conecta Editor (propuesta/revisión/JSON/aplicación), Voz y Fetch; consolida las otras vistas nativas ya presentes y sus servicios. Mantiene adaptadores transitorios para el motor Python existente, con datos por stdin y validaciones de revisión/identidad. La matriz vigente y los pendientes están en `src-gpui/README.md`; no se declara migración íntegra a Rust ni autorización de publicación.

La captura original se conserva separada del texto corregido: sirve como identidad del montaje, mientras la propuesta lleva las correcciones y su nota. La IA consume el texto corregido y su resultado vuelve a vincularse a la captura original antes de validar.

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

### Corrección de alcance y criterio de implementación

Biglex precisó que la migración completa del diseño corresponde a otra agencia. El agente de este chat mantiene exclusivamente lógica/backend y deja preparado el proceso de diseño para esa asignación; la integración frontend anterior queda como antecedente parcial.

El backend se migra con criterio, no por traducción literal. Se aplican mejoras pequeñas o compatibles de eficiencia y coherencia; se comunican los cambios de dirección importantes. Siguiente mejora concreta: planes de edición por deltas y presupuesto de memoria del historial, manteniendo contratos, tiempos y protección de borradores/exportaciones.

Portar el dominio que no requiere Resolve a Rust. Mantener su adaptador de scripting y MCP en Python al inicio. La interfaz consume resultados tipados y comunica errores reales; no crea datos de ejemplo para simular éxito.
GPUI Kit se fija a 0.9.1 para disponer de controles de edición, foco y accesibilidad sobre su snapshot GPUI compatible.

## Criterios de entrega

Compilar y ejecutar en Windows; comprobar importación, edición y exportación reales; pruebas del dominio y errores; registrar el resultado de la consulta real a Resolve según su disponibilidad. Mantener el proceso activo para la migración posterior.
