# DaVinci Flow · Rust + GPUI

Interfaz nativa de escritorio en `main`, versión 1.0.0.

## Ejecutar

`mise dev` abre GPUI desde la raíz de este checkout. `mise setup` prepara los adaptadores para los servicios que todavía los utilizan.

Desde la raíz del repositorio:

```powershell
mise dev
mise dev "ruta/al/archivo.srt"
mise build
mise test
mise check
```

Las cuatro tareas admiten `--plan`. El binario es `target/debug/davinci-flow-gpui.exe`. Windows bloquea el ejecutable mientras está abierto. Luna Fetch usa los ejecutables `yt-dlp` y FFmpeg de `PATH`; FFmpeg también extrae fotogramas. Las operaciones que aún tienen adaptador usan `.venv` o `DAVINCIFLOW_GPUI_PYTHON`. El MCP oficial ejecuta la lectura de subtítulos en el intérprete integrado de Resolve.

## Estado por área

| Área | Implementado | Integración y límites |
|---|---|---|
| Base | Sidebar con identidad activa de proyecto/secuencia, controles compactos, toast superior de estado y ventana inicial 1280 × 900 (mínimo 900 × 640) | Carga inicial silenciosa de ajustes y estado de Resolve |
| Editor | Captura por pista/rango, captura de pista completa, navegación por bloques, SRT, opciones persistentes, tandas reanudables, modo `Decisiones`, propuesta IA o directa, revisión por bloque, JSON, aplicar, limpiar pistas `DF_*` y deshacer | Propuesta directa y por IA, tandas y revisión en Rust. Lectura por MCP oficial, con compatibilidad para el puente anterior. El modo experimental `Decisiones` y la escritura editorial siguen en el adaptador. |
| Corrección | SRT, búsqueda/reemplazo, normalización Unicode, glosario, edición con `Enter`, deshacer/rehacer, exportación UTF-8 y guion con IA | Edición, alineación y preparación de marcadores en Rust. Inserción en Resolve por adaptador. |
| Biblioteca | Carpetas por categoría, sincronización/migración desde `editorial_preferences.json`, inventario y filtros, selección de hasta 80 recursos y limpieza de selecciones no disponibles | Rust; hasta 2000 recursos por listado en UI y 20 000 en propuesta. Preferencias aisladas por checkout en desarrollo |
| B-Rolls | Lista paginada (48 por página) con insignia de formato, selección para IA, vista previa de imagen/fotograma de vídeo e importación directa al Media Pool | Fotograma por FFmpeg; apertura en reproductor del sistema |
| Música | Lista paginada con preescucha e importación al Media Pool | Reproductor nativo de Windows. Importación por MCP oficial. |
| Efectos (SFX) | Catálogo procedural, carpetas del usuario, filtros, ajustes de pista y preescucha | Catálogo y síntesis WAV en Rust. |
| Plantillas | Catálogo instalado, Media Pool, packs, presets, asignación de nodo Text+ y vista previa | Escaneo, presets y lectura de muestras existentes en Rust. Inventario del Media Pool por MCP oficial. Generación de miniaturas mediante el adaptador. |
| Asistente | Consultas y transferencia de dirección creativa al Editor | HTTP directo desde Rust al proveedor configurado. |
| Voz | Voces del sistema, motores Aurora, confirmación de consumo, recuperación, audio externo e importación | SAPI de Windows para voz local. Aurora sigue en el adaptador. Importación por MCP oficial. |
| Luna Fetch | Análisis de URL, descarga de vídeo o audio, carpeta de destino e historial | `yt-dlp` y FFmpeg se ejecutan desde Rust. Importación opcional por MCP oficial. |
| Ajustes | Cuenta de Aurora, proveedor, modelo y clave API | Rust conserva el formato de preferencias del checkout. El acceso autenticado de Aurora sigue en el adaptador. |
| Acerca de | Versión, enlaces oficiales y actualizaciones | Consulta GitHub Releases desde Rust. |

## Contratos y protección del trabajo

- Los tiempos SRT se conservan en milisegundos. La captura original de Resolve permanece intacta; las correcciones pertenecen a las decisiones de la propuesta y llevan nota de edición.
- La propuesta exige revisión explícita antes de aplicar (o confirmación expresa para aprobar los bloques restantes). Cambiar textos o tiempos después de prepararla exige generar otra; Resolve vuelve a comprobar la identidad del montaje.
- SRT y JSON se exportan a archivos nuevos, rechazando sobrescrituras. Los borradores bloquean cambios de fuente y la ventana avisa al cerrar con trabajo sin guardar.
- `SubtitleSession` conserva original, texto, borrador, selección, deltas y recibos de exportación; historial de hasta 32 operaciones y 64 MiB retenidos.
- Las peticiones locales llevan JSON por stdin; las claves y textos no se pasan en la línea de comandos. Las escrituras y generaciones con cobro no se reintentan automáticamente.

## Registro de procesos

- Migración de motor y contratos: `../process/active/2026-11-15_migracion-rust-gpui/`.
- Diseño y paridad visual por pestaña: `../process/active/2026-11-15_diseno-gpui/`.
