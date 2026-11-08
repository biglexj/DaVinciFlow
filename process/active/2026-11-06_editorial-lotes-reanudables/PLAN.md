# Propuestas editoriales por lotes y reanudación

- Estado: `IN_PROGRESS`
- Fecha de inicio: `2026-11-06`
- Responsable: `biglexj`

## Objetivo

Permitir analizar la pista completa de subtítulos en lotes configurables, conservar cada avance para reanudarlo y habilitar modelos con contexto largo según los límites que expone el proveedor.

## Alcance

- Tamaños de tanda: 20, 50, 100, 500 y todos los subtítulos en una petición.
- Flujo manual tanda a tanda y flujo automático para procesar todo lo pendiente.
- Guardado automático por tanda y reanudación comprobando la secuencia fuente.
- Importar una propuesta parcial existente como avance inicial cuando coincida con el tramo actual.
- Filtro activable de modelos de contexto largo con metadatos de capacidad.
- Mantener una sola propuesta completa revisable y aplicable al finalizar.

## Restricciones

- Cambios locales solamente; no publicar ni modificar servicios remotos.
- Preservar cambios previos del espacio de trabajo.
- `controller.py` y `model.py` permanecen fuera de alcance por la reserva documentada en el proceso activo de títulos nativos.
- No cambiar de proveedor o modelo de forma silenciosa.
- Una petición única debe respetar el límite del cliente y mostrar un error útil si no cabe; el modo de procesamiento completo puede dividir automáticamente y guardar cada tanda.

## Criterios de finalización

- El editor permite elegir los tamaños indicados y reanudar desde el primer subtítulo pendiente.
- Los avances se guardan de forma atómica y solo se reutilizan tras verificar que coincide el contenido de la secuencia.
- El filtro de contexto largo muestra modelos disponibles con capacidad suficiente y compatibilidad con salida estructurada.
- Al terminar, la propuesta cubre cada subtítulo exactamente una vez y se aplica/deshace como una sola ejecución.
- `mise build` finaliza correctamente; la revisión visual y funcional en Resolve queda distinguida del build.
