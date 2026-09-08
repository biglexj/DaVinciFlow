# Encargo listo para el diseñador

## Tarea

Diseñar y, cuando Biglex lo asigne, implementar una interfaz clara y adaptable para DaVinci Flow. Conservar el flujo funcional y resolver primero los controles que quedan fuera de pantalla. En este relevo no se ha asignado ni iniciado otro agente.

## Contexto

Corrección explícita de Biglex el 7 de septiembre: recuperar la disposición anterior, con barra lateral vertical a la izquierda y área de trabajo amplia a la derecha. La segunda captura aportada es la referencia elegida. La primera, con pestañas horizontales encima de todo el contenido, representa el diseño rechazado.

Mantener una sola ventana: los botones laterales cambian el panel central sin abrir otro editor. La petición anterior de «pestañas» significaba evitar ventanas adicionales; no exige una barra horizontal superior. Los botones redondeados pueden pulirse dentro de la estructura anterior, sin reemplazarla por otro concepto.

Referencias persistidas: [disposición anterior elegida](references/sidebar-elegido.png) y [disposición superior rechazada](references/pestanas-rechazadas.png).

La implementación antigua permanece en `src/davinci_flow/ui/tkinter_window.py`, función `create_legacy_tkinter_window`, como referencia de composición. Recuperar su estructura visual conservando el motor editorial actual; no restaurar en bloque su lógica ni los botones duplicados de Editor LLM.

El ejemplo de edición combina introducción pequeña, concepto dominante y remate opcional: «un vídeo para / COLOR», o «Intentan aprender / Saltando / entre tutoriales». Debe poder no mostrar texto. El formato horizontal necesita espacio para el montaje; el vertical puede tener mayor densidad. Las plantillas de karaoke del proyecto son opcionales.

Referencia de montaje: [vídeo aportado por Biglex](https://www.youtube.com/watch?v=PIa0-xb5kAY&t=12s). Las capturas que aporta el usuario ilustran la jerarquía, no una instrucción de copiar la marca o la interfaz del autor.

## Formato de entrega

1. Barra lateral vertical: Editor, Plantillas, Biblioteca y Ajustes, con proyecto/secuencia visibles en su cabecera. Si se recupera Asistente (Guion), debe tener una función distinta y real; no duplicar el editor LLM ni añadir paneles vacíos.
2. Estados vacíos, cargando, error, propuesta pendiente, selección de bloque, revisión guardada, aplicación y reversión.
3. Diseño adaptado a ventana pequeña, ampliada y escala de Windows; evidencias de legibilidad y controles alcanzables.
4. Componentes compartidos y cambios de presentación integrados, conservando las acciones existentes.

### Editor

- Jerarquía: fuente → dirección creativa → propuesta → revisión → aplicación.
- Conservar el esquema espacial de la referencia: navegación a la izquierda; controles compactos arriba del área derecha; propuesta amplia debajo. El editor LLM pertenece a este panel central.
- Modo selectivo/completo visible; formato y densidad como opciones de la propuesta, no duplicadas en varias zonas.
- La frase original, la decisión, sus capas, las plantillas elegidas y el motivo deben poder compararse sin abrir otra ventana.
- Un bloque sin rótulo es una decisión válida; diferenciarlo de un error o una fila pendiente.
- Los controles de revisión y aplicación nunca quedan cortados por el alto de la tabla. Usar distribución adaptable, panel desplazable o división ajustable; no resolverlo exigiendo una pantalla más grande.
- Mostrar cuándo cambia el texto respecto a la voz y cuándo falta guardar la revisión. Evitar perder cambios al cambiar de fila, cargar otra propuesta o capturar de nuevo.
- El recurso recomendado y la intención visual son sugerencias; no presentarlos como ya colocados.

### Plantillas

- Distinguir títulos instalados/archivos, Text+ básico y composiciones del proyecto.
- Buscar por nombre; mostrar origen, selección para la LLM y advertencias de compatibilidad.
- Separar «encontrada» de «seleccionada» y de «probada en Resolve».
- Reservar la configuración de nodo/control de Fusion para una sección avanzada. El código conserva un diálogo antiguo, pero esa edición avanzada no está expuesta en el panel nuevo; coordinar su recuperación funcional.
- Vista previa solo si existe evidencia o capacidad real. No inventar miniaturas ni afirmar compatibilidad visual por inventario.

### Biblioteca

- Categorías: Visuals/B-rolls, Efectos de sonido, Música, Títulos/Fusion y Textos/Documentos.
- Cada categoría muestra ruta, cantidad, estado y acciones de elegir/indexar. Dentro de Visuals, distinguir vídeos e imágenes mediante filtros.
- La lista comunica qué recursos se comparten con la LLM; selección vacía y ruta ausente tienen estados claros.
- Mantener un resumen por categoría y búsqueda; evitar repetir cinco formularios enormes junto al editor.
- La música no se presenta como SFX. Las dos pistas de efectos futuras representan funciones sonoras, no dos carpetas obligatorias.

### Ajustes

- Un único modelo seleccionado, persistido y compartido con el editor.
- Clave oculta; conservar la existente si el campo queda vacío.
- Error del proveedor con reintento explícito del mismo modelo y sin simulación de éxito.

## Restricciones

Mantener Python/Tkinter y componentes ligeros salvo nueva decisión de Biglex. Usar los colores propios de Ely/Aurora; consultar el sistema compartido de Docs. Evitar efectos costosos, renderizados constantes o dependencias grandes por decoración. Respetar teclado, foco visible, contraste, tildes y eñes.

No cambiar contratos editoriales, temporización, registros, selección de modelo ni contenido de plantillas para resolver un problema de diseño. Coordinar con el agente funcional si una interacción exige cambiar comportamiento.

## Confirmación en chat

Entregar qué cambió, capturas de los paneles con su barra lateral y prueba de que revisar/aplicar sigue siendo accesible en ventana pequeña. Comparar con la referencia anterior elegida. Separar diseño revisado de funcionamiento LLM/Resolve comprobado.
