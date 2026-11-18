# DaVinci Flow · Rust + GPUI

Migración incremental en `codex/gpui-demo`. Estado: 2026-11-17. Aplicación de desarrollo desde el checkout; todavía no reemplaza la versión instalada. El agente principal vuelve a encargarse tanto del diseño como de la lógica por instrucción de Biglex del 17 de noviembre.

## Ejecutar

Desde la raíz:

```powershell
mise dev-gpui
mise dev-gpui "ruta/al/archivo.srt"
mise build-gpui
mise test-gpui
mise check-gpui
```

Las cuatro tareas admiten `--plan`. El binario es `src-gpui/target/debug/davinci-flow-gpui.exe`; ciérralo antes de recompilar porque Windows bloquea el ejecutable en uso. Requiere Rust y herramientas Windows; los servicios que conservan adaptador usan `.venv` o `DAVINCIFLOW_GPUI_PYTHON`. Las pruebas puras de Rust no requieren Python.

## Estado por área

«Nativa» describe la interfaz y el dominio señalado; no implica paridad completa con Flet.

| Área | Implementado | Integración y límites |
|---|---|---|
| Base | Sidebar conservado, controles compactos, ancho de contenido acotado y ventana inicial 1180 × 800 | Revisión visual final de Biglex pendiente; tamaño mínimo 900 × 640 |
| Editor | Captura por pista/rango, SRT, opciones de formato/densidad/pistas, propuesta directa, revisión por bloque, buscador de plantillas, JSON, aplicar y deshacer | Estado, validación y revisión en Rust; IA y escritor de Resolve por adaptador Python |
| Corrección | SRT, búsqueda/reemplazo, normalización Unicode, glosario, edición, historial, exportación y panel IA/guion | Edición Rust; alineación por proveedor configurado vía Python. Marcadores vinculados a captura identificada; escritura real pendiente de validar |
| Biblioteca | Carpetas por categoría, inventario y filtros, selección de hasta 80 recursos para propuestas | Rust; hasta 2000 recursos por listado. Preferencias propias de GPUI; no sigue enlaces ni carpetas ocultas |
| B-Rolls | Lista compacta, selección para IA, imágenes y fotograma de vídeo, importación explícita | Fotograma por FFmpeg; reproducción con la aplicación del sistema |
| Música | Inventario por categoría y escucha en el reproductor del sistema | Reproductor integrado y controles de audio pendientes |
| SFX | Catálogo real y escucha de WAV del catálogo | Adaptador a los servicios existentes; sin reproducción integrada |
| Plantillas | Catálogo instalado con diagnósticos; selección por capa desde revisión | Presets, edición del catálogo y previsualización de títulos pendientes |
| Asistente | Consultas con el proveedor configurado y transferencia de dirección al Editor | Servicio Python; no sustituye errores por respuestas locales |
| Voz | Voces del sistema/Aurora, cálculo y confirmación de consumo, generación, recuperación e importación | Servicio existente, protección de solicitudes pendientes; prueba real de acceso y generación remota pendiente |
| Luna Fetch | Analizar URL, vídeo MP4/audio MP3, destino, descarga e importación opcional | yt-dlp/FFmpeg por adaptador; progreso numérico y cancelación pendientes |
| Ajustes | Proveedor/modelo, clave enmascarada y cuenta de Aurora con acceso/retorno/cierre de sesión | Misma configuración del checkout Python; no copia sesiones de otras aplicaciones |
| Acerca de | Información y consulta de publicaciones oficiales | No instala actualizaciones ni produce un instalador GPUI |

## Contratos y protección del trabajo

- Los tiempos SRT se conservan en milisegundos. La captura original de Resolve permanece intacta; las correcciones pertenecen a las decisiones de la propuesta y llevan nota de edición.
- La propuesta exige revisión explícita antes de aplicar. Cambiar textos o tiempos después de prepararla exige generar otra; Resolve vuelve a comprobar la identidad del montaje.
- SRT y JSON se exportan a archivos nuevos, rechazando sobrescrituras. Los borradores bloquean cambios de fuente y la ventana avisa al cerrar con trabajo sin guardar.
- `SubtitleSession` conserva original, texto, borrador, selección, deltas y recibos de exportación; historial de hasta 32 operaciones y 64 MiB retenidos. Una respuesta tardía no limpia ediciones posteriores.
- La normalización determinista no inventa tildes ni cambios de significado.
- El inventario se reconstruye desde las carpetas guardadas al entrar en una categoría. Una respuesta de otra categoría se descarta. Preferencias dañadas se notifican y no se sobrescriben.
- Las peticiones locales llevan JSON por stdin; las claves y textos no se pasan en la línea de comandos. Las escrituras y generaciones con cobro no se reintentan automáticamente.
- La voz verifica tarifa y saldo antes de generar. Si Aurora falla, conserva las voces locales realmente instaladas y muestra el error; no inventa saldo ni una sesión válida.

## Qué falta para cerrar la migración

1. Paridad avanzada: tandas reanudables y presets/previsualización de títulos; validación real de alineación semántica/guion/marcadores.
2. Multimedia integrada y progreso/cancelación de descargas.
3. Validación real del ciclo revisado en Resolve, acceso/retorno de Aurora y voz remota; aceptación visual en distintos tamaños.
4. Reducir los adaptadores Python restantes a la frontera que realmente requiere Resolve, migrando los servicios de IA, descarga y autenticación de forma separada.
5. Empaquetado, actualización e instalación de la aplicación GPUI. No hay publicación autorizada ni preparada por estas tareas.

El estado verificable y las pruebas se registran en `process/active/2026-11-15_demo-rust-gpui/VALIDATION.md`. El proceso de diseño se conserva en `process/active/2026-11-15_diseno-gpui/`.

## Organización

- `src/subtitles.rs`, `src/session.rs`: SRT y ciclo de edición.
- `src/editorial.rs`: contrato de propuesta, validación, revisión y vinculación a la fuente.
- `src/library.rs`, `src/preferences.rs`: inventario y persistencia nativos.
- `src/services.rs`, `src/media.rs`, `src/bridge.rs`: contratos tipados y ejecución fuera de la interfaz.
- `src/app/*.rs`: vistas y acciones por área; `src/ui.rs`: primitivas visuales.
- `bridge/*.py`: adaptadores transitorios y retorno de autenticación.
- `tests/test_gpui_bridge.py` en la raíz: pruebas de contratos sin red ni cobros.

GPUI Kit está fijado a `0.9.1`; `Cargo.lock` registra las dependencias. Este incremento aprovecha el motor Python presente en el árbol de trabajo; el checkpoint GPUI no empaqueta ni publica ese motor.
