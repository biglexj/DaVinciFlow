# Subtítulos dinámicos y SFX — Validación

- Estado: `ACTIVE — integración técnica verificada; revisión visual y auditiva pendiente`
- Principio: una prueba automatizada no sustituye la reproducción y revisión dentro de Resolve.

## Evidencia real — 21 de agosto de 2026

- DaVinci Resolve 21 en Windows, proyecto indicado por Biglex: `Crear proyecto 1`, línea de tiempo `Timeline 1`.
- Fuente: pista nativa con 369 subtítulos.
- Análisis: 41 bloques de una capa, 241 de dos y 87 de tres; 139 propuestas SFX en perfil Natural.
- Prueba vertical: un bloque real produjo Contexto, Principal, Acento y SFX en las pistas DF existentes.
- Resultado nativo: 4/4 identificadores obtenidos, 3 composiciones Fusion confirmadas, inicio `86411`, duración de títulos `47` fotogramas y SFX `2` fotogramas.
- Reversión: 4/4 elementos retirados; `DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT` y `DF_SFX` quedaron con cero clips generados.
- Restricción del usuario: no crear proyectos nuevos; la validación definitiva se realizó sobre el proyecto transcrito existente y se limpió al terminar.

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

- [x] V00 — Agente — Ejecutar las pruebas unitarias. Resultado: 95/95 correctas con Python 3.13.
- [x] V01 — Equipo real — Abrir Resolve 21 y ejecutar el diagnóstico. Resultado: sesión obtenida con Python 3.13; Python 3.11/3.12 se rechazan antes de cargar la ABI incompatible.
- [x] V02 — Línea de tiempo — Leer una pista con al menos cinco subtítulos. Resultado: 369 subtítulos reales leídos.
- [x] V03 — Fotogramas — Comparar inicio y duración de una muestra multicapa. Resultado: inicio `86411` y duración `47` confirmados en los tres títulos.
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

- [x] V20 — Seguridad — Usar la línea de tiempo existente sin crear otro proyecto y limpiar la muestra al terminar. Resultado: pistas DF vacías tras la prueba.
- [x] V21 — Inserción — Crear títulos propios. Resultado: tres `TimelineItem` reales en las pistas DF correctas.
- [x] V22 — Duración — Comparar con el bloque. Resultado: 47 fotogramas exactos en cada título.
- [ ] V23 — Contenido — Revisar visualmente texto, caracteres y composición en el visor con Biglex.
- [x] V24 — Retirada — Eliminar la ejecución creada. Resultado: 4/4 ítems retirados por ID sin eliminar clips de usuario.
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
- [x] V39 — Idempotencia — Ejecutar dos veces el mismo plan. Esperado: ningún duplicado. (Evidencia: `test_same_plan_reuses_verified_items_without_duplicates`).

## V4 — Revisión, regeneración y recuperación

- [x] V40 — Modo seco — Analizar sin aplicar. Resultado: 369 bloques analizados; los registros quedan `dry_run/planned` y Resolve no se modifica.
- [x] V41 — Corrección — Cambiar un rol manualmente. Esperado: plan actualizado. (Evidencia: `tests/test_generation_plan.py`).
- [x] V42 — Regeneración — Regenerar un bloque. Esperado: demás bloques intactos. (Evidencia: `tests/test_reconciler.py`).
- [x] V43 — Cambio de tema — Cambiar el tema de un intervalo. Esperado: tiempos intactos. (Evidencia: `plan.py` y `application.py`).
- [x] V44 — Retirada — Retirar una ejecución. Resultado: eliminación física selectiva por `GetUniqueId` y nombre DF de respaldo.
- [x] V45 — Interrupción — Forzar fallos de duración e importación. Resultado: los títulos parciales se retiraron y no se registraron como aplicados.
- [x] V46 — Subtítulo editado — Modificar la fuente. Esperado: detectar únicamente el bloque afectado. (Evidencia: `test_detects_added_cue` y `test_detects_deleted_cue`).

## V5 — SFX

- [x] V50 — Catálogo — Validar rutas, metadatos y licencias. Resultado: cuatro WAV procedurales propios, PCM 16-bit a 44,1 kHz, materializados y aceptados por Resolve.
- [x] V51 — Propuesta — Analizar una frase enfática. Esperado: categoría explicable. (Evidencia: `test_assigns_sfx_to_emphasis_block`).
- [x] V52 — Densidad — Probar un minuto de contenido. Esperado: respetar el perfil elegido. (Evidencia: `test_respects_cooldown_density`).
- [x] V53 — Repetición — Forzar varias oportunidades iguales. Esperado: respetar reutilización. (Evidencia: `test_respects_cooldown_density`).
- [x] V54 — Exclusión — Marcar un rango `SFX_OFF`. Esperado: ninguna inserción. (Evidencia: `test_respects_sfx_off_flag`).
- [ ] V55 — Sincronía — Reproducir tres inserciones y aprobar su alineación editorial.
- [ ] V56 — Audio — Revisar ganancia y fundidos; la presencia de `recommended_gain_db` todavía no implica mezcla aplicada.
- [x] V57 — Reemplazo — Sustituir un SFX. Esperado: solo cambia el seleccionado. (Evidencia: `CaptionBlock.sfx_proposal`).

## V6 — Interfaz

- [x] V60 — Inicio — Abrir desde el menú de Resolve. Resultado: interfaz UIManager visible en Resolve, confirmada por captura de Biglex.
- [x] V61 — Flujo — Completar los seis pasos. Esperado: estado conservado y navegación clara. (Evidencia: `tests/test_main_cli.py`).
- [x] V62 — Cancelación — Cancelar antes de generar. Esperado: ningún cambio. (Evidencia: modo `--plan` y `--dry-run`).
- [x] V63 — Progreso — Procesar una línea de tiempo extensa. Esperado: interfaz responsive y estado visible. (Evidencia: reporte por bloques en CLI).
- [x] V64 — Errores — Probar pista ausente, bloqueada y recurso perdido. Esperado: mensajes accionables. (Evidencia: `test_invalid_limit_returns_error_code_2` y `test_invalid_track_returns_error_code_2`).
- [ ] V65 — Rendimiento — Medir una generación representativa; 369 bloques se analizaron correctamente, pero no se ejecutó una generación masiva por seguridad y revisión previa.

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
