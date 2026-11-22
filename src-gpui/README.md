# DaVinci Flow · Rust + GPUI

Interfaz nativa de escritorio en `main`, versión 1.0.0.

## Ejecutar

`mise dev` abre GPUI desde `DaVinciFlow`. `mise dev py` abre Flet 1.0.0 desde la rama `v-python`, en la carpeta de trabajo hermana `DaVinciFlow-Flet`. La edición Python queda como alternativa y el desarrollo continúa en Rust. Los adaptadores de GPUI siguen usando `src/davinci_flow/` para Resolve, IA, voz y descargas.

Desde la raíz del repositorio:

```powershell
mise dev
mise dev "ruta/al/archivo.srt"
mise dev py
mise build-gpui
mise test-gpui
mise check-gpui
```

Las cuatro tareas admiten `--plan`. El binario es `src-gpui/target/debug/davinci-flow-gpui.exe`; ciérralo antes de recompilar porque Windows bloquea el ejecutable en uso. Requiere Rust y herramientas Windows; los servicios que conservan adaptador usan `.venv` o `DAVINCIFLOW_GPUI_PYTHON`. Las pruebas puras de Rust no requieren Python.

## Estado por área

| Área | Implementado | Integración y límites |
|---|---|---|
| Base | Sidebar con identidad activa de proyecto/secuencia, controles compactos, toast superior de estado y ventana inicial 1280 × 900 (mínimo 900 × 640) | Carga inicial silenciosa de ajustes y estado de Resolve |
| Editor | Captura por pista/rango, captura de pista completa, navegación por bloques (`◀ Ant.` / `Sig. ▶`), SRT, opciones persistentes (Modo, Formato, Densidad, Pistas, Tanda, Dirección), tandas reanudables (`Generar tanda`), modo experimental `Decisiones`, propuesta IA o directa, tabla de 7 columnas, mesa de revisión por bloque (con original, motivo, imagen sugerida, plantilla por capa según `track_mode` y selector SFX), JSON, aplicar con confirmación de pendientes, gestión de colisiones (`EditorialConflictError`), limpiar pistas `DF_*` y deshacer | Estado, validación y revisión en Rust; IA, tandas y escritor de Resolve por adaptador Python |
| Corrección | SRT, búsqueda/reemplazo, normalización Unicode, glosario, edición con `Enter` para guardar y avanzar, historial Undo/Redo (32 ops / 64 MiB), exportación UTF-8 sin sobrescritura y panel IA/guion con marcador dinámico de proveedor | Edición en Rust; alineación semántica e inserción de marcadores vía Python |
| Biblioteca | Carpetas por categoría, sincronización/migración desde `editorial_preferences.json`, inventario y filtros, selección de hasta 80 recursos y limpieza de selecciones no disponibles | Rust; hasta 2000 recursos por listado en UI y 20 000 en propuesta. Preferencias aisladas por checkout en desarrollo |
| B-Rolls | Lista paginada (48 por página) con insignia de formato, selección para IA, vista previa de imagen/fotograma de vídeo e importación directa al Media Pool | Fotograma por FFmpeg; apertura en reproductor del sistema |
| Música | Lista paginada con preescucha Play/Detener e importación directa a Resolve | WAV en proceso (`winsound`); otros formatos en reproductor del sistema |
| Efectos (SFX) | Fusión del catálogo procedural oficial y las carpetas SFX del usuario por subcarpeta, buscador, filtros por categoría, ajustes de pista (`DF_SFX`) y anticipación (`-3`), preescucha Play/Detener y copia de ruta al portapapeles | Adaptador a los servicios existentes y `global_sound_player` |
| Plantillas | Catálogo instalado + Media Pool del proyecto (`Leer proyecto`), filtros por categoría/fuente, packs rápidos de 1 clic (`Nativos`, `Shorts`, `YouTube`, `Noticiero`, `Text+ Básico`), presets guardados (`Mis presets`), asignación de nodo/control Text+ y modal de vista previa de diseño | Escaneo, presets y captura de miniaturas por adaptador Python |
| Asistente | Consultas con el proveedor configurado y transferencia de dirección creativa al Editor | Servicio Python; no sustituye errores por respuestas locales |
| Voz | Separación por motor (`Voces del sistema · Gratis` y motores de Aurora) y voz dependiente, estimación en vivo, cálculo y confirmación de consumo, generación local/remota, recuperación, selección de audio externo, enlace a Voice Studio web e importación a «DaVinci Flow · Voces» | Servicio existente, protección de solicitudes pendientes y cobros |
| Luna Fetch | Analizar URL con autodetección de solo audio, insignias de duración y plataforma, vídeo MP4 / audio MP3, carpeta de destino, importación automática e historial de descargas de la sesión | `yt-dlp` / FFmpeg por adaptador |
| Ajustes | Cuenta de Aurora (inicio con Google y Discord, detección automática del callback de retorno, cancelación, plan/saldo y cierre de sesión) y configuración de proveedor/modelo/clave API enmascarada | Misma configuración del checkout Python; no copia sesiones de otras aplicaciones |
| Acerca de | Versión de la aplicación, enlaces oficiales y panel de actualizaciones | Consulta GitHub Releases |

## Contratos y protección del trabajo

- Los tiempos SRT se conservan en milisegundos. La captura original de Resolve permanece intacta; las correcciones pertenecen a las decisiones de la propuesta y llevan nota de edición.
- La propuesta exige revisión explícita antes de aplicar (o confirmación expresa para aprobar los bloques restantes). Cambiar textos o tiempos después de prepararla exige generar otra; Resolve vuelve a comprobar la identidad del montaje.
- SRT y JSON se exportan a archivos nuevos, rechazando sobrescrituras. Los borradores bloquean cambios de fuente y la ventana avisa al cerrar con trabajo sin guardar.
- `SubtitleSession` conserva original, texto, borrador, selección, deltas y recibos de exportación; historial de hasta 32 operaciones y 64 MiB retenidos.
- Las peticiones locales llevan JSON por stdin; las claves y textos no se pasan en la línea de comandos. Las escrituras y generaciones con cobro no se reintentan automáticamente.

## Registro de procesos

- Migración de motor y contratos: `process/active/2026-11-15_migracion-rust-gpui/`.
- Diseño y paridad visual por pestaña: `process/active/2026-11-15_diseno-gpui/`.
