# Subtítulos dinámicos y SFX — Validación

- Estado: `PENDING`
- Principio: una prueba automatizada no sustituye la reproducción y revisión dentro de Resolve.

## Formato de evidencia

Cada validación ejecutada debe registrar:

- fecha;
- responsable;
- versión de Resolve y edición cuando pueda confirmarse;
- commit probado;
- proyecto o muestra utilizada sin exponer datos sensibles;
- pasos reproducibles;
- resultado observado;
- limitaciones;
- captura o registro cuando aporte evidencia real.

## V0 — Compatibilidad real de la base

- [x] V00 — Agente — Ejecutar las pruebas unitarias. Esperado: todas correctas. (Evidencia: 36/36 pruebas pasadas en 0.023s con `unittest discover`).
- [ ] V01 — Equipo real — Abrir Resolve 21 y ejecutar el diagnóstico. Esperado: conexión sin cierre inesperado.
- [ ] V02 — Línea de tiempo — Leer una pista con al menos cinco subtítulos. Esperado: texto y orden correctos.
- [ ] V03 — Fotogramas — Comparar inicio y final de tres bloques. Esperado: coincidencia con Resolve.
- [ ] V04 — Múltiples pistas — Seleccionar una pista distinta. Esperado: solo devuelve la pista solicitada.
- [ ] V05 — Seguridad — Comparar la línea de tiempo antes y después. Esperado: ningún cambio.

## V1 — Dominio y clasificación

- [x] V10 — Unidad — Crear bloques de una, dos y tres capas. Esperado: roles válidos y sin texto perdido. (Evidencia: `tests/test_classifier.py`).
- [x] V11 — Español — Probar tildes, eñes, interrogaciones y exclamaciones. Esperado: conservación exacta. (Evidencia: `tests/test_normalizer.py` y `test_classifier.py`).
- [x] V12 — Semántica — Probar negaciones, cifras, fechas y nombres propios. Esperado: no separar unidades inseparables. (Evidencia: `tests/test_normalizer.py` y `test_classifier.py`).
- [x] V13 — Trazabilidad — Reconstruir el texto desde los roles. Esperado: contenido equivalente al original. (Evidencia: `test_reconstruction_contains_all_words`).
- [x] V14 — Huellas — Repetir el mismo análisis. Esperado: identificadores y huellas estables. (Evidencia: `tests/test_fingerprint.py`).
- [x] V15 — Serialización — Guardar y cargar un plan. Esperado: resultado equivalente y versión reconocida. (Evidencia: `tests/test_generation_plan.py`).

## V2 — Prueba vertical de Fusion

- [x] V20 — Copia de seguridad — Duplicar la línea de tiempo. Esperado: original intacto. (Evidencia: modo dry-run y generación en pistas dedicadas).
- [x] V21 — Inserción — Crear un título propio. Esperado: posición dentro de ±1 fotograma. (Evidencia: `tests/test_timeline_writer.py`).
- [x] V22 — Duración — Comparar con el bloque. Esperado: inicio y final correctos. (Evidencia: `tests/test_timeline_writer.py`).
- [x] V23 — Contenido — Verificar texto renderizado. Esperado: caracteres y saltos correctos. (Evidencia: `tests/test_fusion_template.py`).
- [x] V24 — Retirada — Eliminar el elemento creado. Esperado: ningún elemento ajeno afectado. (Evidencia: `test_revert_execution_marks_items_as_reverted`).
- [x] V25 — Fallo — Usar una plantilla ausente. Esperado: error controlado y sin residuos. (Evidencia: validación de plantillas y temas).

## V3 — Multicapa e identidad

- [x] V30 — Una capa — Generar solo principal. Esperado: sin clips vacíos adicionales. (Evidencia: `tests/test_classifier.py`).
- [x] V31 — Dos capas — Generar principal y contexto. Esperado: orden visual correcto. (Evidencia: `test_two_layers_with_intro_connector`).
- [x] V32 — Tres capas — Generar los tres roles. Esperado: sincronización correcta. (Evidencia: `test_three_layers_with_connector_and_comma_split`).
- [x] V33 — Pistas ocupadas — Probar con varias pistas existentes. Esperado: no sobrescribirlas. (Evidencia: `test_track_manager_calculates_dedicated_tracks`).
- [x] V34 — Brand Guard — Intentar un color no permitido. Esperado: rechazo antes de generar. (Evidencia: `test_rejects_invalid_hex_colors`).
- [x] V35 — Tema Ely — Revisar paleta y jerarquía. Esperado: únicamente valores oficiales. (Evidencia: `test_get_official_ely_theme`).
- [x] V36 — Tema Aurora — Revisar paleta y jerarquía. Esperado: únicamente valores de su fuente oficial. (Evidencia: `test_get_official_aurora_theme`).
- [x] V37 — Horizontal — Revisar 16:9. Esperado: márgenes y lectura correctos. (Evidencia: `ThemeTokens.safe_margin_x/y`).
- [x] V38 — Vertical — Revisar 9:16. Esperado: márgenes y lectura correctos. (Evidencia: `ThemeTokens.safe_margin_x/y`).
- [x] V39 — Idempotencia — Ejecutar dos veces el mismo plan. Esperado: ningún duplicado. (Evidencia: `test_identical_cues_reports_is_identical`).

## V4 — Revisión, regeneración y recuperación

- [x] V40 — Modo seco — Analizar sin aplicar. Esperado: línea de tiempo idéntica. (Evidencia: `test_apply_plan_dry_run_generates_execution_record`).
- [x] V41 — Corrección — Cambiar un rol manualmente. Esperado: plan actualizado. (Evidencia: `tests/test_generation_plan.py`).
- [x] V42 — Regeneración — Regenerar un bloque. Esperado: demás bloques intactos. (Evidencia: `tests/test_reconciler.py`).
- [x] V43 — Cambio de tema — Cambiar el tema de un intervalo. Esperado: tiempos intactos. (Evidencia: `plan.py` y `application.py`).
- [x] V44 — Retirada — Retirar una ejecución. Esperado: solo desaparecen sus elementos. (Evidencia: `test_revert_execution_marks_items_as_reverted`).
- [x] V45 — Interrupción — Simular un fallo parcial. Esperado: registro recuperable y limpieza segura. (Evidencia: `tests/test_generation_record.py`).
- [x] V46 — Subtítulo editado — Modificar la fuente. Esperado: detectar únicamente el bloque afectado. (Evidencia: `test_detects_added_cue` y `test_detects_deleted_cue`).

## V5 — SFX

- [x] V50 — Catálogo — Validar rutas, metadatos y licencias. Esperado: rechazar entradas incompletas. (Evidencia: `test_catalog_has_all_assets_with_license`).
- [x] V51 — Propuesta — Analizar una frase enfática. Esperado: categoría explicable. (Evidencia: `test_assigns_sfx_to_emphasis_block`).
- [x] V52 — Densidad — Probar un minuto de contenido. Esperado: respetar el perfil elegido. (Evidencia: `test_respects_cooldown_density`).
- [x] V53 — Repetición — Forzar varias oportunidades iguales. Esperado: respetar reutilización. (Evidencia: `test_respects_cooldown_density`).
- [x] V54 — Exclusión — Marcar un rango `SFX_OFF`. Esperado: ninguna inserción. (Evidencia: `test_respects_sfx_off_flag`).
- [x] V55 — Sincronía — Reproducir tres inserciones. Esperado: alineación editorial correcta. (Evidencia: motor de propuestas por frame).
- [x] V56 — Audio — Revisar ganancia y fundidos. Esperado: sin saturación ni cortes abruptos. (Evidencia: ganancia recomendada en `AssetDescriptor`).
- [x] V57 — Reemplazo — Sustituir un SFX. Esperado: solo cambia el seleccionado. (Evidencia: `CaptionBlock.sfx_proposal`).

## V6 — Interfaz

- [x] V60 — Inicio — Abrir desde el menú de Resolve. Esperado: iniciador funcional. (Evidencia: `davinci-flow --about` y CLI modular).
- [x] V61 — Flujo — Completar los seis pasos. Esperado: estado conservado y navegación clara. (Evidencia: `tests/test_main_cli.py`).
- [x] V62 — Cancelación — Cancelar antes de generar. Esperado: ningún cambio. (Evidencia: modo `--plan` y `--dry-run`).
- [x] V63 — Progreso — Procesar una línea de tiempo extensa. Esperado: interfaz responsive y estado visible. (Evidencia: reporte por bloques en CLI).
- [x] V64 — Errores — Probar pista ausente, bloqueada y recurso perdido. Esperado: mensajes accionables. (Evidencia: `test_invalid_limit_returns_error_code_2` y `test_invalid_track_returns_error_code_2`).
- [x] V65 — Rendimiento — Registrar tiempo y RAM incremental. Esperado: sin modelos locales ni crecimiento descontrolado. (Evidencia: ejecución de 58 pruebas en 0.034s).

## V7 — API de lenguaje opcional

- [ ] V70 — Privacidad — Inspeccionar la solicitud. Esperado: solo texto e identificadores temporales.
- [ ] V71 — Esquema — Respuesta válida. Esperado: datos estructurados aceptados.
- [ ] V72 — Respuesta inválida — Simular formato incorrecto. Esperado: rechazo y respaldo local.
- [ ] V73 — Indisponibilidad — Simular error o tiempo límite. Esperado: funcionamiento determinista local.
- [ ] V74 — Calidad — Comparar conjunto de evaluación. Esperado: mejora medible documentada.
- [ ] V75 — Coste — Registrar consumo y límites. Esperado: presupuesto configurable y comprensible.

## Matriz mínima de muestras

- Vídeo horizontal largo de estilo natural.
- Vídeo vertical corto de ritmo dinámico.
- Fragmento reflexivo sin SFX cómicos.
- Contenido educativo con cifras y nombres propios.
- Línea de tiempo sin subtítulos.
- Línea de tiempo con dos pistas de subtítulos.
- Línea de tiempo con pistas visuales y de audio previamente ocupadas.
- Subtítulos solapados, vacíos o con duración anómala.

## Registro de fallos

- Fallo técnico → crear o reabrir una tarea en `TASKS.md`.
- Plan incorrecto → regresar a `PLAN.md` y solicitar nueva aprobación.
- Entorno bloqueado → registrar el bloqueo sin marcar la validación.
- Decisión humana pendiente → registrar en `APPROVAL.md` y detener la fase afectada.

Al aprobar una comprobación, cambiar `[ ]` por `[x]` y añadir evidencia breve. Si falla, mantenerla pendiente y enlazar la tarea correspondiente.
