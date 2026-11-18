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
- [ ] Verificar guardado/reapertura del JSON completo desde el diálogo nativo; el contrato Rust/Python sí dispone de prueba de integración.
- [ ] Validar aplicación/deshacer reales sobre una secuencia de prueba de Resolve.
- [ ] Validar acceso/retorno y generación remota de Aurora con el usuario.
- [ ] Paridad avanzada, multimedia integrada, adaptadores restantes e instalador: ver matriz `src-gpui/README.md`.
