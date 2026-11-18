# Validación del frontend

> Evidencia de los incrementos de diseño ejecutados en esta sesión. Las tareas
> pendientes figuran en `TASKS.md`. Las comprobaciones siguientes no acreditan paridad
> total con Flet ni aceptación visual por parte de Biglex.

## Primer incremento: ventana y módulos con motor propio

- Ventana nativa reorganizada según la interfaz Flet vigente: barra lateral con las
  once pestañas y sus nombres, encabezado con el módulo activo, área de trabajo y pie
  de estado. La pestaña «Conexión» de la demo anterior se disolvió: la consulta de
  Resolve vive ahora dentro del Editor, como en Flet.
- «Corrección» con la disposición vigente: resumen y acciones, herramientas rápidas
  (buscar/reemplazar, mayúsculas/minúsculas, normalizar, glosario), contador, editor
  de bloque y tabla con estado por fila.
- «Biblioteca» por categorías con carpetas configurables, indexado real y selección
  de hasta 80 recursos.
- «Editor» con las tres etapas, captura desde Resolve con pista y rango, carga de SRT
  y tabla de subtítulos de origen.
- Diálogo «Acerca de» con la información oficial vigente y sus enlaces.

### Comprobaciones estáticas

- [x] `cargo check --manifest-path src-gpui/Cargo.toml --locked --all-targets`: correcto.
- [x] `cargo clippy --manifest-path src-gpui/Cargo.toml --locked --all-targets -- -D warnings`: correcto.
- [x] `cargo fmt --manifest-path src-gpui/Cargo.toml`: aplicado.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked`: 37 pruebas correctas;
      se añadieron las del glosario y la restauración de un bloque.

### Contrato de sesión

- [x] `app.rs` sigue consumiendo `SubtitleSession` como fuente única del documento,
      selección, borrador, cambios pendientes e historial. Las vistas no mutan
      bloques ni declaran su propio estado de cambios.
- [x] La exportación sigue pasando por `export_snapshot`, `save_new` en el executor y
      `accept_export` al volver. La interfaz no declara el documento guardado.
- [x] El glosario y la restauración de un bloque se resuelven en el motor Rust
      (`apply_glossary`, `restore_cue`); las vistas solo invocan acciones.

### Prueba nativa

- [x] Ventana abierta en Windows con la disposición vigente y las once pestañas.
- [x] SRT cargado por línea de órdenes: la tabla muestra los tres bloques con sus
      tiempos, el editor de bloque queda abierto sobre el primero y el contador
      marca «3 subtítulos en total · 0 corregidos».
- [x] Consulta real a Resolve: «Comprobar conexión» devolvió «Resolve está abierto y
      responde al MCP oficial» y «Capturar Resolve» leyó la pista 1 del montaje
      «¿POR QUÉ TERMINAR UNA HISTORIA NOS DEJA VACÍOS / Voz + B-Roll · 24 fps» con
      120 subtítulos, que aparecen en la tabla con sus tiempos.
- [x] Errores reales en el pie: «Aplicar glosario» sin términos informa
      «Ingresa términos de glosario (ej: término: Reemplazo)» sin alterar el
      documento.
- [ ] Exportación desde esta ventana comprobada con el parser vigente: el diálogo de
      guardado es nativo y no se automatizó en esta prueba.

## Segundo incremento: módulos con servicios del proyecto

- Puente de servicios (`src-gpui/bridge/services.py`) con operaciones explícitas:
  `settings`, `scan_models`, `assistant`, `release`, `sfx_catalog`, `templates`,
  `save_key` y `save_settings`. Comparte el protocolo local por stdin con el resto de
  adaptadores.
- «Asistente IA» con el contexto de la secuencia, las cuatro sugerencias de la
  interfaz vigente, el hilo de mensajes y la transferencia de la primera frase como
  «Dirección creativa».
- «Ajustes» con proveedor, modelo, escaneo del catálogo, credencial enmascarada y
  guardado en la configuración estándar del usuario.
- «Efectos (SFX)» con el catálogo oficial, «Plantillas» con las 694 plantillas
  instaladas y su etiqueta de origen, «B-Rolls» y «Música» sobre el motor de
  biblioteca.
- Panel de actualizaciones dentro de «Acerca de», con el estado real de la consulta.

### Comprobaciones

- [x] `cargo check --manifest-path src-gpui/Cargo.toml --locked --all-targets`: correcto.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked`: 41 pruebas correctas.
- [x] `settings` real: proveedor `gemini`, modelo `gemini-4-carbon`, credencial
      configurada y preferencias editoriales vigentes.
- [x] `scan_models` real: 10 modelos de Gemini disponibles.
- [x] `sfx_catalog` real: 8 efectos del catálogo oficial.
- [x] `templates` real: 694 plantillas instaladas con su origen.
- [x] `assistant` real: la consulta llega a Gemini y devuelve el error de cuota del
      proveedor (HTTP 429) en lugar de una respuesta inventada; la interfaz lo
      comunica en el pie.
- [x] Ventana: «Ajustes» muestra el modelo y la credencial enmascarada; «Efectos»,
      «Plantillas» y «Asistente» muestran sus datos reales.

## Tercer incremento: panel semántico de Corrección

- Panel «Alineación semántica y corrección con IA (Gemini)» dentro de «Corrección»,
  con el guion de referencia, la detección de marcadores en la línea de tiempo, el
  botón de corrección y la inserción de marcadores en Resolve.
- El motor aplica el resultado de forma transaccional: `SubtitleSession::apply_texts`
  rechaza textos vacíos, líneas en blanco o listas que no correspondan a los bloques
  cargados, y conserva los tiempos.
- Puente: operaciones `align` e `insert_markers` en `src-gpui/bridge/services.py`,
  con el mismo protocolo local por stdin.

### Comprobaciones

- [x] `cargo check`, `cargo fmt` y `cargo clippy -- -D warnings`: correctos.
- [x] `cargo test --manifest-path src-gpui/Cargo.toml --locked`: 45 pruebas correctas;
      se añadió la del cambio de textos por IA.
- [x] `align` real: la petición llega a Gemini y devuelve el error de cuota del
      proveedor (HTTP 429) en lugar de una respuesta inventada.
- [x] Ventana: el panel se abre y cierra desde «Alternar panel IA / Guion» y muestra
      guion, marcador y las dos acciones; «Insertar marcadores en Resolve» permanece
      deshabilitado hasta que la IA devuelve marcadores.

## Pendiente de validación

- [ ] Revisión visual y funcional de Biglex. La comprobación estática y las capturas
      de la ventana no equivalen a aceptación del diseño.
- [ ] Previsualización de audio y vídeo en la biblioteca y los catálogos.

No se modificó Flet ni la instalación estable. La ventana nativa comparte con Flet
las rutas estándar de credenciales y preferencias editoriales; el resto de datos de
la biblioteca nativa viven en su propio archivo.

## Continuación del 2026-11-17

El agente principal retoma también diseño según la petición actual. Mantiene el sidebar, acota formularios, compacta tarjetas/listas y elimina la expansión vertical del área de mensajes vacía. B-Rolls combina lista y vista previa; la reproducción se abre con el sistema.

Se observó la carga de 20 subtítulos y su propuesta directa en la mesa GPUI. Compilación final alternativa correcta (el ejecutable estándar estaba abierto), formato/Clippy correctos, 45 pruebas Rust más 1 integración explícita y 47 pruebas Python seleccionadas correctas.

Pendientes: aceptación visual de Biglex, navegación/resizes completos, guardado mediante el diálogo nativo y pruebas reales de Resolve/Aurora/multimedia. Evidencia y límites: ../2026-11-15_demo-rust-gpui/VALIDATION.md. Matriz vigente: src-gpui/README.md. Las secciones previas son antecedentes.
