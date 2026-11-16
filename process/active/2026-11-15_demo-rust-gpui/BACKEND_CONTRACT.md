# Contrato de sesión Rust para el frontend

Acuerdo de integración del 2026-11-15. El agente de este chat mantiene `davinci_flow_gpui::session::SubtitleSession`; la agencia encargada del frontend lo consume desde `app.rs`. Las vistas no duplican sus reglas.

## Lectura

- `SubtitleSession::default()` crea una sesión vacía.
- `document(&self) -> &Document`: fuente, bloques y avisos actuales.
- `selected(&self) -> Option<usize>`: bloque seleccionado.
- `draft(&self) -> &str`: texto del editor.
- `has_draft(&self) -> bool`: diferencia entre editor y bloque guardado.
- `is_dirty(&self) -> bool`: cambios respecto al último estado cargado/exportado, no respecto al texto original de forma permanente.
- `filtered_indices(&self, query: &str) -> Vec<usize>`: búsqueda sin distinguir mayúsculas en original y texto actual.
- `can_undo(&self) -> bool`, `can_redo(&self) -> bool`: disponibilidad del historial.

El historial conserva hasta 32 operaciones por deltas de texto, con un presupuesto de 64 MiB para los textos y las reservas de los vectores retenidos. Las entradas antiguas pueden caducar antes por memoria. Una operación que supera por sí sola el presupuesto falla sin modificar el documento ni borrar Rehacer. No conserva copias de los tiempos ni modifica Resolve.

## Acciones

Todas las acciones que pueden fallar devuelven `Result<_, String>` con un mensaje utilizable. Un fallo no modifica parcialmente la sesión.

- `load(&mut self, document: Document) -> Result<(), String>`: rechaza sustituir una fuente con cambios/borrador pendientes; selecciona el primer bloque al cargar.
- `select(&mut self, index: usize) -> Result<(), String>`: valida el índice y exige guardar o descartar el borrador anterior.
- `set_draft(&mut self, text: String)`: actualiza el editor en memoria.
- `discard_draft(&mut self)`: vuelve al texto guardado del bloque.
- `save_draft(&mut self) -> Result<usize, String>`: guarda un texto no vacío, elimina líneas vacías internas que romperían SRT y conserva los tiempos; devuelve 0 o 1 bloques modificados.
- `normalize(&mut self) -> Result<usize, String>` y `replace(&mut self, find: &str, replacement: &str, case_sensitive: bool) -> Result<usize, String>`: operaciones por lote transaccionales.
- `restore_all(&mut self) -> Result<usize, String>`: restaura los originales y recalcula los cambios respecto al último guardado/exportación. Se puede deshacer.
- `undo(&mut self) -> Result<(), String>` / `redo(&mut self) -> Result<(), String>`: historial de texto de la sesión, sin modificar tiempos ni Resolve.

## Exportación fuera del hilo de interfaz

1. `export_snapshot(&self) -> Result<ExportSnapshot, String>` produce una copia inmutable, solo sin borradores y con documento válido.
2. En el executor: `snapshot.save_new(&path) -> Result<ExportReceipt, String>` escribe UTF-8 en un destino nuevo; no sobreescribe archivos.
3. Al volver a la interfaz: `accept_export(&mut self, receipt: ExportReceipt) -> Result<(), String>` registra exactamente qué estado se exportó. Una respuesta tardía no borra cambios hechos después y no se admite un recibo de otra sesión.

`save_new` consume el snapshot. El recibo ofrece `path(&self) -> &Path` y solo se crea después de confirmar la escritura; sus datos internos son privados. También se rechaza un recibo anterior a una exportación ya registrada.

No se usa `dirty = false` en la vista como sustituto de este registro. El recibo no incluye credenciales ni autoriza operaciones en Resolve.

## Integración

El editor visual mantiene su `TextareaState`; al recibir `InputEvent::Change` llama a `set_draft(value)`. Después de seleccionar, cargar, guardar, restaurar o deshacer, sincroniza el control desde `draft()`. Los cambios programáticos del control pueden emitir `Change`; asignar el mismo texto debe ser inocuo.

`Document`, `Cue`, `library::Inventory` y las funciones de lectura de `bridge` conservan su API inicial. El agente principal avisará cuando el módulo esté listo para compilar. La integración GPUI y la incorporación visible de deshacer/rehacer pertenecen al agente de frontend.
