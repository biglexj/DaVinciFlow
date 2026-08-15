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

- [ ] V00 — Agente — Ejecutar las pruebas unitarias. Esperado: todas correctas.
- [ ] V01 — Equipo real — Abrir Resolve 21 y ejecutar el diagnóstico. Esperado: conexión sin cierre inesperado.
- [ ] V02 — Línea de tiempo — Leer una pista con al menos cinco subtítulos. Esperado: texto y orden correctos.
- [ ] V03 — Fotogramas — Comparar inicio y final de tres bloques. Esperado: coincidencia con Resolve.
- [ ] V04 — Múltiples pistas — Seleccionar una pista distinta. Esperado: solo devuelve la pista solicitada.
- [ ] V05 — Seguridad — Comparar la línea de tiempo antes y después. Esperado: ningún cambio.

## V1 — Dominio y clasificación

- [ ] V10 — Unidad — Crear bloques de una, dos y tres capas. Esperado: roles válidos y sin texto perdido.
- [ ] V11 — Español — Probar tildes, eñes, interrogaciones y exclamaciones. Esperado: conservación exacta.
- [ ] V12 — Semántica — Probar negaciones, cifras, fechas y nombres propios. Esperado: no separar unidades inseparables.
- [ ] V13 — Trazabilidad — Reconstruir el texto desde los roles. Esperado: contenido equivalente al original.
- [ ] V14 — Huellas — Repetir el mismo análisis. Esperado: identificadores y huellas estables.
- [ ] V15 — Serialización — Guardar y cargar un plan. Esperado: resultado equivalente y versión reconocida.

## V2 — Prueba vertical de Fusion

- [ ] V20 — Copia de seguridad — Duplicar la línea de tiempo. Esperado: original intacto.
- [ ] V21 — Inserción — Crear un título propio. Esperado: posición dentro de ±1 fotograma.
- [ ] V22 — Duración — Comparar con el bloque. Esperado: inicio y final correctos.
- [ ] V23 — Contenido — Verificar texto renderizado. Esperado: caracteres y saltos correctos.
- [ ] V24 — Retirada — Eliminar el elemento creado. Esperado: ningún elemento ajeno afectado.
- [ ] V25 — Fallo — Usar una plantilla ausente. Esperado: error controlado y sin residuos.

## V3 — Multicapa e identidad

- [ ] V30 — Una capa — Generar solo principal. Esperado: sin clips vacíos adicionales.
- [ ] V31 — Dos capas — Generar principal y contexto. Esperado: orden visual correcto.
- [ ] V32 — Tres capas — Generar los tres roles. Esperado: sincronización correcta.
- [ ] V33 — Pistas ocupadas — Probar con varias pistas existentes. Esperado: no sobrescribirlas.
- [ ] V34 — Brand Guard — Intentar un color no permitido. Esperado: rechazo antes de generar.
- [ ] V35 — Tema Ely — Revisar paleta y jerarquía. Esperado: únicamente valores oficiales.
- [ ] V36 — Tema Aurora — Revisar paleta y jerarquía. Esperado: únicamente valores de su fuente oficial.
- [ ] V37 — Horizontal — Revisar 16:9. Esperado: márgenes y lectura correctos.
- [ ] V38 — Vertical — Revisar 9:16. Esperado: márgenes y lectura correctos.
- [ ] V39 — Idempotencia — Ejecutar dos veces el mismo plan. Esperado: ningún duplicado.

## V4 — Revisión, regeneración y recuperación

- [ ] V40 — Modo seco — Analizar sin aplicar. Esperado: línea de tiempo idéntica.
- [ ] V41 — Corrección — Cambiar un rol manualmente. Esperado: plan actualizado.
- [ ] V42 — Regeneración — Regenerar un bloque. Esperado: demás bloques intactos.
- [ ] V43 — Cambio de tema — Cambiar el tema de un intervalo. Esperado: tiempos intactos.
- [ ] V44 — Retirada — Retirar una ejecución. Esperado: solo desaparecen sus elementos.
- [ ] V45 — Interrupción — Simular un fallo parcial. Esperado: registro recuperable y limpieza segura.
- [ ] V46 — Subtítulo editado — Modificar la fuente. Esperado: detectar únicamente el bloque afectado.

## V5 — SFX

- [ ] V50 — Catálogo — Validar rutas, metadatos y licencias. Esperado: rechazar entradas incompletas.
- [ ] V51 — Propuesta — Analizar una frase enfática. Esperado: categoría explicable.
- [ ] V52 — Densidad — Probar un minuto de contenido. Esperado: respetar el perfil elegido.
- [ ] V53 — Repetición — Forzar varias oportunidades iguales. Esperado: respetar reutilización.
- [ ] V54 — Exclusión — Marcar un rango `SFX_OFF`. Esperado: ninguna inserción.
- [ ] V55 — Sincronía — Reproducir tres inserciones. Esperado: alineación editorial correcta.
- [ ] V56 — Audio — Revisar ganancia y fundidos. Esperado: sin saturación ni cortes abruptos.
- [ ] V57 — Reemplazo — Sustituir un SFX. Esperado: solo cambia el seleccionado.

## V6 — Interfaz

- [ ] V60 — Inicio — Abrir desde el menú de Resolve. Esperado: iniciador funcional.
- [ ] V61 — Flujo — Completar los seis pasos. Esperado: estado conservado y navegación clara.
- [ ] V62 — Cancelación — Cancelar antes de generar. Esperado: ningún cambio.
- [ ] V63 — Progreso — Procesar una línea de tiempo extensa. Esperado: interfaz responsive y estado visible.
- [ ] V64 — Errores — Probar pista ausente, bloqueada y recurso perdido. Esperado: mensajes accionables.
- [ ] V65 — Rendimiento — Registrar tiempo y RAM incremental. Esperado: sin modelos locales ni crecimiento descontrolado.

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
