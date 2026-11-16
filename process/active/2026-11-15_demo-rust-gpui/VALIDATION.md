# Validación · 2026-11-15

## Comprobaciones automatizadas

- [x] `mise build-gpui`: binario nativo de Windows compilado con el toolchain estable actual (`x86_64-pc-windows-gnullvm`).
- [x] `mise test-gpui`: **10 pruebas correctas**. Cubren Unicode español, SRT/BOM/CRLF/tags, conservación de milisegundos, rechazo explícito de bloques inválidos, reemplazo literal/transaccional, normalización transaccional, origen de Resolve, exportación UTF-8 sin sobrescritura, inventario real/ocultos/límites y fallos de protocolo.
- [x] `mise check-gpui`: formato y Clippy de todos los targets, sin advertencias (`-D warnings`).
- [x] `mise tasks --json`: aparecen `dev-gpui`, `build-gpui`, `check-gpui`, `test-gpui`.
- [x] `mise dev-gpui --plan` y `mise dev-gpui --plan temp/gpui-qa/captura-local-20.srt`: muestran el comando sin lanzar Cargo ni la aplicación.
- [x] `mise dev-gpui --help`: ayuda específica de la demo.

## Verificación nativa por Computer Use

- [x] Ventana ejecutada y observada en Windows, con navegación y los tokens de color actuales del producto. El ejecutable final quedó abierto con el SRT de la captura anterior.
- [x] Apertura mediante el selector nativo de `temp/gpui-qa/captura-local-20.srt`.
  Este SRT se obtuvo de la captura local anterior `temp/editorial-highlights/snapshot.json` (**20 cues**, 24 fps, origen 86400), restando su origen. No es una lectura en vivo de la sesión actual.
- [x] Los bloques se muestran en la lista virtualizada y el primero aparece en el editor. Durante la revisión se corrigió un contenedor sin layout flex que dejaba el listado sin altura; se reconfirmó en la ventana.
- [x] Editar el primer texto y pulsar **Guardar cambio**; se actualiza la lista y el contador. Los controles de exportación se deshabilitan mientras queda un borrador pendiente.
- [x] Intentar cerrar con cambios muestra **Hay cambios sin exportar**. Escape vuelve a la aplicación conservando el texto.
- [x] Exportar desde el diálogo nativo a `temp/gpui-qa/exportado-ui.srt`.
  Lectura independiente con `davinci_flow.subtitles.srt_parser.load_srt_file`: **20 cues**, todos los tiempos coinciden con la entrada, solo cambia el primer texto y el archivo es UTF-8 válido.
- [x] Biblioteca: elegir `assets` con el selector nativo y obtener sus **3 imágenes reales**; el inventario muestra las rutas relativas.
- [x] Conexión: el puente real devuelve `running: false`, transporte MCP y versión informada 21.1; la ventana muestra **Resolve no disponible**, sin afirmar conexión correcta.
- [x] Tras el ajuste de ancho de filas y los colores de las acciones se recompiló, pasó Clippy y se observó el ejecutable final.

## Pendiente y límites

- [ ] Capturar subtítulos con Resolve abierto. Estaba cerrado y no se abrió ni se modificó ningún proyecto para esta demo.
- [ ] Paridad completa con Corrección Flet (glosario, IA, sincronización al Editor).
- [ ] Reproducción, carátulas, rutas de biblioteca por categoría e importación al Media Pool.
- [ ] Aceptación visual y funcional de Biglex. La revisión del agente no la sustituye.

No se ejecutó la suite Python completa: no se cambió el motor ni la interfaz Flet. La validación de compatibilidad se centró en el parser existente y la consulta real del puente. No se generó instalador ni se publicó una versión.

## Segundo incremento: separación de responsabilidades y sesión Rust

- [x] Un único proceso adicional para diseño/frontend, delegado a otro agente con propiedad de archivos explícita y preservación de identidad/flujos. El motor continúa en este proceso.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked --lib -j 4`: **26 pruebas correctas**. Las 16 nuevas comprueban borradores pendientes, carga inválida/otras fuentes, edición sin cambios de tiempos, operaciones transaccionales, undo/redo, límites del historial, búsqueda, restauración después de exportar y recibos tardíos/de otra carga/fuera de orden.
- [x] Escritura real de snapshot/recibo en prueba: SRT UTF-8 legible, rechazo de sobrescritura y estado pendiente conservado ante fallos.
- [x] El agente delegado comprobó check de todos los targets, formato y Clippy `-D warnings`, sin advertencias.
- [x] `mise build-gpui`: compilación final de la integración correcta.
- [x] Antes de actualizar el ejecutable se observó la demo anterior con 0 bloques editados y sin borrador pendiente; se cerró normalmente, sin descartar cambios del usuario.
- [x] Prueba en la ventana integrada: editar el primer bloque, guardar, **Deshacer** (vuelve al original), **Rehacer** (recupera la edición) y exportar mediante el diálogo nativo a `temp/gpui-qa/exportado-sesion-ui.srt`.
- [x] Verificación independiente del archivo anterior mediante el parser Python vigente: **20 cues**, todos los tiempos iguales a `captura-local-20.srt`, solo cambia el primer texto. La fuente original permanece intacta.
- [x] Observación final: la aplicación comunica la ruta exportada y deja de mostrar cambios sin exportar. Se conservan paleta, tipografía, navegación, tres pestañas y disposición lista/editor; Deshacer/Rehacer se añaden junto al contador.

La demo quedó ejecutándose con la copia de revisión en memoria. La captura en Resolve abierto y la aceptación de Biglex continúan pendientes; este incremento no las sustituye.
