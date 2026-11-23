# Tareas

- [x] Revisar checkout e instrucciones y crear `codex/gpui-demo`.
- [x] Base de ventana, navegación y controles GPUI.
- [x] Migrar dominio SRT y corrección a Rust.
- [x] Migrar inventario local de biblioteca a Rust.
- [x] Conectar lectura de estado/subtítulos de Resolve al puente existente.
- [x] Comandos Mise y guía de continuidad por pestañas.
- [x] Compilación, pruebas y verificación de SRT/biblioteca/estado en Windows.
- [x] Separar diseño/frontend en un único proceso nuevo y delegarlo conservando identidad y flujos.
- [x] Definir el contrato de sesión e implementar el ciclo de edición independiente de GPUI.
- [x] Incorporar historial de 32 operaciones, validación de borradores y exportación por copia/recibo.
- [x] Verificar 26 pruebas del motor e integrar guardar/deshacer/rehacer/exportar desde la ventana.
- [x] Preparar el encargo completo de diseño para la otra agencia tras la corrección de alcance de Biglex.
- [x] Sustituir copias completas por planes de edición por bloque, con conteo incremental de cambios pendientes.
- [x] Acotar el historial a 64 MiB y 32 operaciones, preservando documento/borrador/redo si un cambio excede el presupuesto.
- [x] Verificar 32 pruebas y Clippy de todos los targets, sin modificar frontend.
- [x] Validar captura con Resolve abierto: la pista 1 del montaje «¿POR QUÉ TERMINAR
      UNA HISTORIA NOS DEJA VACÍOS / Voz + B-Roll · 24 fps» devolvió 120 subtítulos.
- [x] Motor ampliado para el diseño migrado: glosario por términos, restauración de un
      bloque, categorías y extensiones de biblioteca y preferencias propias de la
      ventana nativa.
- [x] Primer flujo de Editor/Plantillas: propuesta directa, revisión por bloque, selección de plantilla por capa y exportación JSON.

## Continuación del 2026-11-17

- [x] Asumir también diseño según la nueva instrucción; conservar sidebar y compactar tarjetas/formularios.
- [x] Contrato editorial Rust con validación, revisión, notas y protección de la captura original.
- [x] Conectar generación de propuesta, aplicación y deshacer al motor Python actual sin reintentos de escritura.
- [x] Añadir Voz y Luna Fetch con contratos tipados y acciones reales; cuenta en Ajustes.
- [x] Listas compactas de medios con vista previa de imagen/fotograma, reproductor externo e importación explícita.
- [x] JSON por stdin, clave enmascarada, validación de tarifa/saldo y preferencias dañadas protegidas.
- [x] Integrar guion/IA de Corrección con deltas atómicos y proveedor explícito; rechazar marcadores sin captura identificada o con montaje diferente.
- [x] Verificar apertura real de 20 subtítulos y propuesta directa en la mesa nativa.
- [x] Renombrar rama a `GPUI`, actualizar versión a `0.3.1`, retirar referencias de demo y dividir `app.rs` (`subtitles_actions.rs`) para cumplir el límite de líneas (< 900).
- [x] Unificar aislamiento por checkout e importación de rutas desde `editorial_preferences.json`, persistiendo opciones del Editor y mostrando identidad activa en el sidebar.
- [x] Completar paridad de controles en Editor/Revisión (tabla de 7 columnas, tandas reanudables, modo Decisiones, SFX por bloque, capas según `track_mode`, limpiar pistas DF y colisiones `EditorialConflictError`).
- [x] Completar paridad de Plantillas (packs rápidos, presets, lectura de proyecto Media Pool, asignación de nodo Text+ y vista previa modal), SFX (fusión con carpetas de usuario, filtros y preescucha), Voz (separación motor/voz, Discord y autodetección de callback) y Luna Fetch (metadatos enriquecidos e historial de sesión).
- [ ] Verificar guardado/reapertura del JSON completo desde el diálogo nativo; el contrato Rust/Python sí dispone de prueba de integración.
- [ ] Validar aplicación/deshacer reales sobre una secuencia de prueba de Resolve.
- [ ] Validar acceso/retorno y generación remota de Aurora con el usuario.
- [ ] Aceptación visual y funcional de Biglex e integración final en el instalador.

## Consolidación de Rust del 2026-11-22

- [x] Conservar Flet 1.0.0 en la rama remota `v-python` y mantener `mise dev py` como su entrada.
- [x] Migrar ajustes, credenciales por proveedor, asistente, corrección por lotes y consulta de actualizaciones.
- [x] Migrar propuesta editorial estándar y avance por tandas. Recuperar avances compatibles y conservar la transcripción corregida como entrada.
- [x] Migrar catálogo local y presets de plantillas, muestras de paquetes DRFX y síntesis WAV de SFX.
- [x] Ejecutar Luna Fetch y la extracción de fotogramas desde Rust. Sintetizar voces locales con SAPI.
- [x] Conectar Rust directamente al MCP oficial para estado, lectura de subtítulos, inventario del Media Pool e importación.
- [ ] Verificar captura con subtítulos e importación sobre un proyecto de prueba de Resolve.
- [ ] Migrar el modo experimental `Decisiones`, la generación de miniaturas en Resolve y la escritura editorial, incluidos marcadores, subtítulos, aplicación y reversión.
- [ ] Migrar autenticación, generación y recuperación de voz de Aurora.
- [ ] Consolidar el instalador Rust y retirar los adaptadores y herramientas Python de la edición activa cuando pasen las pruebas de paridad.
