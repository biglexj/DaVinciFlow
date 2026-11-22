# Validación · 2026-11-15

## Promoción de GPUI · 2026-11-22

Biglex fijó `mise dev` para GPUI en `main` y `mise dev py` para Python/Flet en la rama `Python`. El selector localiza la carpeta de trabajo de `Python` desde `main`. Si falta, la prepara desde la rama local o remota. `--plan` muestra el destino sin crear la carpeta.

Se abrió una ventana por cada comando desde la carpeta principal. Pasaron 496 pruebas de Python/Flet, 53 pruebas de Rust y 15 pruebas del puente Python de GPUI. `mise check-gpui` y la compilación nativa pasaron. La rama `Python` se subió a GitHub en `2076d14` con versión 1.0.0.

## Separación de carpetas de trabajo · 2026-11-22

Git registra el cambio de nombre de `codex/gpui-demo` a `GPUI` en `aa772b1`. La raíz `DaVinciFlow` está en `GPUI`. La carpeta hermana `DaVinciFlow-Flet` es un `git worktree` en `codex/flet-local`, derivada de `main` en `00b5527`.

Se copiaron 141 archivos locales vinculados a Flet, el motor Python, el empaquetado y sus documentos. Se verificaron byte a byte los 23 archivos modificados o nuevos de `src-flet/` en la nueva carpeta y en `temp/orden-worktrees-2026-11-22/cambios-interfaz-flet.zip`. El `src-flet/` de `GPUI` volvió al contenido de su commit base. El motor Python sigue disponible en ambos árboles para sus respectivos servicios. Se conservaron los cambios preparados en el índice.

Flet tiene su propio `.venv` y el lockfile sincronizado con su manifiesto local. Pasaron `mise check` y 28 pruebas seleccionadas de Flet. Pasaron `mise check-gpui` y 15 pruebas de su puente Python. Los planes de arranque apuntan a cada carpeta y `main` conserva `00b5527`.

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

## Tercer incremento: mejoras del backend sin traducción literal

- [x] Proceso de diseño ampliado a todas las áreas Flet y preparado para la agencia que Biglex asigne. El agente de este chat conserva lógica/backend.
- [x] `Document` genera planes transaccionales con los bloques cambiados. La sesión reutiliza esos planes para normalizar/reemplazar sin clonar el documento entero.
- [x] Guardar un bloque construye un cambio individual. El número de bloques pendientes se actualiza por los índices afectados; solo se recalcula completo al registrar una exportación.
- [x] Historial limitado por 32 operaciones y 64 MiB de textos/reservas de vectores retenidos. Undo/Redo mueve las mismas entradas sin contar dos veces su memoria. Un cambio individual excesivo se rechaza antes de alterar el documento o borrar la rama Rehacer.
- [x] `mise test-gpui`: **32 pruebas correctas**, incluidas seis nuevas de planes por bloque, presupuesto de historial, rechazo atómico, contabilidad Undo/Redo y cambios pendientes frente al último exportado.
- [x] `mise check-gpui`: formato y Clippy de todos los targets correctos, sin advertencias. Las firmas públicas del controlador no cambian y el frontend existente sigue pasando la comprobación.
- [x] En este incremento no se modifican `app.rs`, `app/views.rs`, `ui.rs` ni `main.rs`.

No se midió aceleración temporal ni se afirma un límite global de RAM: el presupuesto se aplica al historial retenido. La demo abierta conserva el binario del incremento anterior; las nuevas optimizaciones están comprobadas en las pruebas compiladas del motor y requieren recompilar la demo para ejecutarlas en la ventana. No se intervino de nuevo en el diseño.

## Cuarto incremento: motor al servicio del diseño migrado

Ejecutado junto con el [proceso de diseño](../2026-11-15_diseno-gpui/PLAN.md), que Biglex asignó a esta sesión el 2026-11-15.

- [x] `SubtitleSession::apply_glossary`: interpreta «término: Reemplazo» y «término -> Reemplazo», sustituye palabras completas sin distinguir mayúsculas, rechaza entradas inválidas y es transaccional.
- [x] `SubtitleSession::restore_cue`: restaura el texto original de un bloque concreto, conserva los demás cambios y se puede deshacer.
- [x] `library`: categorías y extensiones vigentes (B-rolls, Efectos, Música, Títulos y Fusion, Textos y documentos), índice estable por recurso y avisos por carpeta inexistente.
- [x] `preferences`: preferencias propias de la ventana nativa en `~/.davinci_flow/gpui/library.json`, escritura atómica y límite de 80 recursos compartidos. No se toca el archivo de preferencias de Flet.
- [x] Puente de Resolve: la lectura admite pista y rango (`subtitles track=… first=… last=…`), valida los argumentos y devuelve un error utilizable.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked`: **37 pruebas correctas** (cuatro nuevas: glosario, glosario sin palabras parciales y restauración de un bloque).
- [x] `cargo clippy --manifest-path src-gpui/Cargo.toml --locked --all-targets -- -D warnings`: correcto.
- [x] Consulta real al puente con Resolve abierto: `status` devuelve `running: false` con transporte MCP disponible y `subtitles` devuelve 120 cues de la pista 1 del montaje abierto.

La captura en la ventana nativa, la exportación y la aceptación visual de Biglex quedan registradas en el proceso de diseño. No se modificó la interfaz Flet ni el motor compartido con Python, salvo el adaptador de lectura ya descrito.

## Continuación del 2026-11-17: lógica y diseño

- Alcance: agente principal asume también presentación. Sidebar conservado, tarjetas/formularios compactados, anchos acotados y listas virtualizadas. Todas las entradas tienen vistas conectadas; no se declara paridad completa.
- Editor: propuesta directa, revisión por bloque/capa y buscador de plantillas; JSON sin sobrescritura; generación IA, aplicar y deshacer conectados. La captura original conserva la identidad de Resolve; las correcciones pertenecen a decisiones con nota. La IA consume el texto corregido y su resultado vuelve a vincularse al original.
- Voz/Fetch: contratos tipados y vistas nativas sobre los servicios Python actuales. Cuenta en Ajustes, clave enmascarada, solicitudes por stdin, consumo confirmado y recuperación sin reintentos facturables automáticos.
- Corrección semántica: guion/IA integrado con proveedor explícito y lote de textos atómico. Marcadores rechazados sin captura o si cambia el montaje; posición/inserción reales pendientes.
- Biblioteca: reconstrucción por categoría fuera del render, descarte de respuestas de otra categoría y navegación pendiente retomada al terminar un trabajo. Preferencias dañadas notificadas sin sobrescritura.

### Verificación técnica final

- `mise check-gpui`: formato y Clippy de todos los targets con `-D warnings`, correcto.
- `mise test-gpui`: **45 pruebas Rust correctas**, 1 integración excluida por defecto.
- `cargo test --manifest-path src-gpui/Cargo.toml --locked --lib native_proposals -- --ignored`: **1 integración correcta**. El contrato Python rechaza aplicar sin revisión y acepta la propuesta aprobada. Sin llamadas IA ni escritura en Resolve.
- `PYTHONPATH=src;tests .venv/Scripts/python.exe -m unittest tests.test_gpui_bridge tests.test_fetch tests.test_system_tts tests.test_voice_catalog tests.test_voice_media tests.test_aurora_voice`: **47 pruebas correctas**, sin cobros ni escritura real en Resolve.
- `mise build-gpui` pasó durante el incremento. El último intento no pudo reemplazar el ejecutable estándar porque estaba abierto (Windows, acceso denegado). El estado final compiló con `cargo rustc --manifest-path src-gpui/Cargo.toml --locked --bin davinci-flow-gpui -- -o temp/gpui-qa/davinci-flow-gpui-preview.exe`. Sus dos avisos se deben al uso de `-o` junto con las salidas de Cargo; el chequeo estricto ordinario no tiene advertencias.
- Copia final: `temp/gpui-qa/DaVinciFlow-GPUI-preview-2026-11-17.exe`; SHA-256 `2FFA4DBC4F28E8DEAA2DD2168836C172A6A656E1D19C440D7E01DD3AD24557E3`.
- Se antepuso la toolchain estable al PATH de las verificaciones porque los shims iniciales no respondían; no se cambió la configuración del usuario.

### Verificación funcional y visual

- Instancia GPUI aislada: abrió `temp/gpui-qa/captura-local-20.srt` con **20 bloques**. «Preparar revisión directa» abrió la mesa con **0 de 20 revisados**, texto real y plantillas instaladas.
- Se observó Editor/revisión en ventana de 1180 × 800. Los últimos ajustes de buscador/cuenta/espaciado se compilaron; no se volvió a completar toda la navegación visual. La aceptación corresponde a Biglex.
- «Guardar JSON» abrió su diálogo nativo; el guardado completo por ese diálogo quedó sin confirmar durante el uso concurrente/captura de pantalla. La prueba Rust de exportación/reapertura y rechazo de sobrescritura sí pasó.
- Voz local real: **4 voces instaladas**, un WAV generado y **55 645 fotogramas** validados. Archivo `~/.davinci_flow/development/5e4f2d1334263063/gpui/voice/330d2ebf-463b-45a7-b953-d1659366765c.wav`. No se probó la escucha.

### Límites

No se ejecutaron aplicación/deshacer ni marcadores reales en Resolve, acceso/retorno de Aurora, voz remota con créditos o descarga real de un enlace elegido por el usuario. No hay migración íntegra del motor a Rust, instalador GPUI ni publicación. El checkpoint GPUI utiliza el motor Python presente en el árbol, que conserva cambios previos ajenos a este incremento.

## Cierre de paridad y renombrado a `GPUI` (2026-11-17)

- [x] Rama renombrada `codex/gpui-demo` → `GPUI`; carpeta de proceso renombrada a `2026-11-15_migracion-rust-gpui`; eliminado el módulo inactivo `src-gpui/src/app/pending.rs`.
- [x] Sincronizada versión `0.3.1` en `src-gpui/Cargo.toml`, título de ventana `DaVinci Flow (Desarrollo)` / `DaVinci Flow`, tamaño inicial `1280 × 900` y retirado el término «demo» de interfaz, `Cargo.toml`, `mise.toml` y `scripts/gpui-task.ts`.
- [x] `app.rs` dividido extrayendo `src-gpui/src/app/subtitles_actions.rs` (401 líneas), dejando `app.rs` en 644 líneas y todos los módulos bajo el límite de 900 líneas.
- [x] Preferencias en `src-gpui/src/preferences.rs` aisladas por checkout en desarrollo e importando automáticamente carpetas desde `editorial_preferences.json`; `Options::default()` alineado a `mode = "highlights"`, carga inicial silenciosa de ajustes y estado de Resolve, y persistencia automática al cambiar opciones del Editor.
- [x] Identidad del proyecto y línea de tiempo en la barra lateral (`shell.rs`) tomada tanto de capturas/propuestas como de transcripciones SRT y estado de Resolve.
- [x] Paridad de controles en Editor y Mesa de Revisión: captura de pista completa, avance/retroceso de rango, tandas reanudables (`batch_next`), modo experimental `Decisiones` (`generate_decisions`), tabla de 7 columnas, motivo e imagen sugerida de la IA, selector de SFX por bloque, capas visibles según `track_mode`, confirmación antes de aprobar pendientes al aplicar, botón «Limpiar pistas DF» y manejo estructurado de colisiones (`EditorialConflictError`).
- [x] Paridad en Plantillas (packs rápidos de 1 clic, presets guardados, lectura del Media Pool del proyecto, asignación de nodo Text+, origen `Text+ básico` y vista previa modal), SFX (fusión con carpetas de usuario, filtros por categoría, pista/anticipación, preescucha Play/Detener y copia al portapapeles), Voz (selectores dependientes de motor y voz, Google/Discord, autodetección de callback de retorno, estimación en vivo y selección de audio local) y Luna Fetch (insignias de duración/extractor, autodetección de solo audio e historial de sesión).
- [x] `cargo fmt --manifest-path src-gpui/Cargo.toml -- --check` y `cargo clippy --manifest-path src-gpui/Cargo.toml --locked --all-targets -- -D warnings`: **0 advertencias**.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked --lib`: **45 pruebas en verde** (+ 1 prueba de integración Rust↔Python `--ignored` en verde).
- [x] `PYTHONPATH=src;tests .venv/Scripts/python.exe -m unittest tests.test_gpui_bridge`: **13 pruebas en verde** (incluida la prueba nueva de colisiones estructuradas `EditorialConflictError`).
- [x] Entrada por defecto cambiada a GPUI (`mise dev`, `mise dev gpui`, `mise dev-gpui`, `scripts/start-desktop.ps1`, `python -m davinci_flow.ui`, `python -m davinci_flow --ui`), conservando `--flet` / `mise dev-flet` como respaldo explícito.
- [x] Icono oficial de ventana y barra de tareas (`assets/branding/icons/icon-windows.ico`) aplicado en la ventana nativa Win32 (`WM_SETICON` + `app_id = com.biglexj.davinciflow`).
- [x] Diseño a ancho completo (`size_full()` / `w_full()`) en todas las vistas, sección superior del Editor dividida en dos columnas («Tramo y fuente» y «Captura de subtítulos en Resolve o SRT»), voces en rejilla multicolumna con botones de mayor altura, tarjetas de «Ajustes» en 2 columnas (Cuenta de Aurora + Modelo de IA) y diálogo «Acerca de» ampliado (`580 px`) con los 4 botones de apoyo oficial en cuadrícula 2×2.
- [x] Reproductor nativo integrado de música y audio (`src-gpui/src/audio_player.rs` + `src-gpui/src/app/player_bar.rs`) sobre WinMM MCI en hilo persistente con caché WAV automática vía FFmpeg para `.m4a`/`.flac`/`.ogg`/`.aac`/`.opus`, cola de reproducción en **Música** y **Efectos (SFX)**, reproducción interna en **Generación de voz** y **Luna Fetch (Audio)** sin abrir reproductores externos/Prisma, barra de progreso interactiva, salto `-10s`/`+10s`, bucle y control de volumen/silencio.
- [x] Verificación posterior (`2026-11-18`): `mise run check-gpui` sin advertencias, `mise run test-gpui` **48 pruebas en verde** (incluidas 3 nuevas de `audio_player`) y `mise run build-gpui` compilado en verde.
- [x] Integración de vídeo nativo y refinamiento de UI (`2026-11-18`): reproductor de vídeo en vivo (`src-gpui/src/video_player.rs` sobre FFmpeg MJPEG + `RenderImage` con `window.drop_image` y reloj de audio/silencio en `audio_player.rs`), reproductor acotado exclusivamente a su sección activa (**B-Rolls**, **Música**, **Efectos (SFX)**, **Luna Fetch** y barra compacta dentro de «Audio generado» en **Generación de voz**), botones de acción multimedia de ancho fijo (`fixed_media_button`, `118 px`) sin saltos al alternar `Reproducir`/`Pausar`/`Reanudar`, y rejilla de **Generación de voz** en **4 columnas × máximo 3 filas visibles** con alineación exacta (`flex_basis(px(0.))`).
- [x] Comprobación final (`2026-11-18`): `mise run check-gpui` (`0` advertencias), `mise run test-gpui` (**51 pruebas en verde**), `mise run build-gpui` en verde y todos los módulos bajo 900 líneas.
