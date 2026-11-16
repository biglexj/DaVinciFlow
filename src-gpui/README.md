# DaVinci Flow · demo Rust + GPUI

Migración incremental en la rama `codex/gpui-demo`. Se ejecuta desde el checkout; no sustituye el ejecutable instalado ni cambia la versión de DaVinci Flow.

## Abrir

Desde la raíz del repositorio:

```powershell
mise dev-gpui
# Opcional: abrir un SRT real al iniciar
mise dev-gpui "ruta/al/archivo.srt"
```

Requisitos: Rust estable con herramientas de compilación para Windows. La lectura de Resolve reutiliza `.venv` y su puente actual; SRT y biblioteca funcionan íntegramente en Rust sin Python. Para un intérprete diferente se admite `DAVINCIFLOW_GPUI_PYTHON`.

```powershell
mise build-gpui
mise test-gpui
mise check-gpui
mise dev-gpui --plan
```

Las cuatro tareas admiten `--plan`, que muestra los comandos sin ejecutarlos. El binario de desarrollo queda en `src-gpui/target/debug/davinci-flow-gpui.exe`. La demo no dispone de tareas de release o publicación.

## Qué funciona

- **Corrección**: importar SRT UTF-8/BOM o Latin-1; listado virtualizado; filtrar; editar y guardar un bloque; buscar/reemplazar literal con opción de mayúsculas; normalizar NFC, espacios y puntuación; restaurar la fuente; deshacer/rehacer hasta 32 operaciones de texto; exportar una copia SRT UTF-8.
- **Biblioteca**: seleccionar una carpeta, inventariar vídeo/audio/imágenes/títulos/documentos, filtrar, actualizar y mostrar un archivo en el Explorador. No sigue enlaces simbólicos ni recorre carpetas ocultas. Informa errores y limita el inventario a 2000 recursos.
- **Conexión**: consultar disponibilidad real de Resolve mediante su MCP oficial y capturar la pista 1 a través del adaptador existente. Una consulta fallida no genera una captura de sustitución.

La exportación crea un archivo nuevo y rechaza destinos existentes; no sobreescribe la fuente. Los cambios se guardan en memoria hasta exportarlos. La ventana advierte antes de cerrar con cambios. Una edición pendiente debe guardarse o descartarse antes de cambiar de bloque o exportar.

`SubtitleSession` mantiene el documento, borrador, selección, historial y estado de exportación en el motor Rust. Una exportación registra exactamente la copia que escribió: una respuesta tardía conserva las ediciones posteriores y un recibo de otra carga se rechaza. Restaurar el original después de exportar una corrección vuelve a contar como cambio pendiente.

La normalización determinista no inventa tildes ni corrige semántica. Los tiempos SRT permanecen en milisegundos; al capturar Resolve se resta el origen de la secuencia para exportar tiempos relativos. Los bloques SRT inválidos causan un error explícito, en vez de desaparecer del documento. Los solapamientos válidos se conservan con aviso.

## Continuar por pestañas

| Base / pestaña | Primer incremento | Pendiente |
|---|---|---|
| Base | Ventana, tema vigente, navegación, errores, trabajo en segundo plano | Preferencias de ventana y accesibilidad completa |
| Corrección | SRT y edición local en Rust; captura por puente | Glosario, corrección IA, sincronización al Editor |
| Biblioteca | Inventario local en Rust | Rutas por categoría, carátulas, reproducción, importación a Resolve |
| Conexión | Estado y captura | Selección de pista/rango y controles de escritura revisada |
| Editor / Plantillas | Motor Python conservado | Propuesta, revisión, presets, aplicación y deshacer |
| Voz / SFX / B-Rolls / Música / Luna Fetch | Implementaciones actuales conservadas | Migración y reproducción multimedia |
| Ajustes / actualizaciones / Acerca de | Implementación actual conservada | Contratos nativos y empaquetado |

No se muestran pestañas vacías para capacidades pendientes. No se han migrado las credenciales ni las sesiones de Aurora a un almacenamiento nuevo.

## Código

- `src/subtitles.rs`: dominio SRT y corrección; sin controles GPUI.
- `src/session.rs`: ciclo de edición, historial, validaciones y seguimiento de exportaciones; independiente de GPUI.
- `src/session_tests.rs`: pruebas del ciclo completo y de respuestas tardías/otras sesiones.
- `src/library.rs`: inventario local; sin decodificación multimedia.
- `src/bridge.rs` y `bridge/read_resolve.py`: proceso de solo lectura, resultado JSON tipado y tiempo límite.
- `src/app.rs`: estado y coordinación de acciones.
- `src/app/views.rs` y `src/ui.rs`: vistas y primitivas con los colores actuales de Flet.

GPUI Kit se fija a `0.9.1`; `Cargo.lock` registra sus dependencias. El proceso y la evidencia viven en `process/active/2026-11-15_demo-rust-gpui/`.

El diseño/frontend se delega por separado en `process/active/2026-11-15_diseno-gpui/`, con la instrucción de conservar la identidad, distribución y flujos actuales. El contrato entre motor e interfaz está en `process/active/2026-11-15_demo-rust-gpui/BACKEND_CONTRACT.md`.
