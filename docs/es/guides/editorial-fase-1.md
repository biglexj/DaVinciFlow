# Editor editorial de fase 1

Abrir con `python -m davinci_flow --editorial-ui` usando Python 3.13 y el paquete instalado o `PYTHONPATH=src`. También está disponible desde las interfaces existentes. Abrir esta ventana carga tres Text+ básicos incluidos y no conecta con Resolve. Desde Revisar y generar con LLM, la captura sí se realiza al pulsar el botón.

## Trabajo offline

1. Abrir un SRT e indicar sus FPS.
2. Leer títulos instalados o elegir una carpeta de `.setting`, `.comp` o paquetes `.drfx`.
3. Configurar catálogo: seleccionar pocas plantillas conocidas para ofrecer a la LLM. El inventario no garantiza compatibilidad visual.
4. Si hay varios textos, indicar `Nodo::Control`, por ejemplo `MiTitulo::Input1`. Los controles expuestos identificables se rellenan automáticamente. El nodo vacío exige un único Text+ accesible.
5. Elegir el modelo exacto y proponer con LLM. Se utiliza la credencial local existente; no se incluye en la propuesta guardada.
6. Revisar cada bloque: textos, plantillas e inclusión. Cambiar palabras requiere una nota explícita. Guardar la revisión del bloque antes de cambiar de fila o aplicar.
7. Guardar o abrir el JSON editorial, distinto de los planes locales históricos.

Una propuesta SRT offline no se aplica a una secuencia sin identidad comprobada. Para escribir, capturar subtítulos nativos del montaje final y analizar esa captura. Las capas comparten el intervalo del subtítulo: no se inventan tiempos por palabra.

## Uso en Resolve

1. Preparar una secuencia de prueba de 30–60 segundos ya cortada y con subtítulos nativos.
2. Incluir composiciones propias en la bandeja `DaVinci Flow` del Media Pool; la captura no la crea.
3. Elegir pista y rango de subtítulos; capturar explícitamente. Límite inicial: 120 subtítulos por propuesta.
4. Elegir una plantilla instalada y otra del proyecto, analizar y revisar.
5. Aplicar. Solo se crean `DF_CONTEXT`, `DF_MAIN` y `DF_ACCENT`; se comprueban pista, posición, duración y texto.
6. Reproducir: verificar legibilidad, superposición de capas, animaciones y recursos externos. Las plantillas conservan su diseño; no se recolorean ni reposicionan automáticamente.
7. Reaplicar sin duplicar y deshacer. Para otra revisión, deshacer la anterior primero; la regeneración selectiva pertenece a fase 2.

Se rechazan cambios en la secuencia, archivos de plantilla modificados, pistas bloqueadas y clips ajenos solapados. Un texto generado editado manualmente tampoco se sobrescribe silenciosamente.

## Compatibilidad y límites

- `.drfx`: inventario sin extraer medios. La extracción ocurre al aplicar, dentro de la caché y preservando jerarquía de recursos. Los paquetes ilegibles se reportan.
- `.setting`: se conserva el árbol interno y se añade MediaOut si la salida se identifica. Composiciones ambiguas necesitan preparación manual en el Media Pool.
- Configurar duración no demuestra adaptación estética de keyframes fijos. Anim Curves es el mecanismo recomendado por la documentación instalada para duración variable; revisar cada plantilla.
- Media Pool: identidad por ID, modificación en copia insertada. Cambios internos de una plantilla conservando el mismo ID requieren revisión manual.
- Prueba real realizada el 6 de septiembre de 2026: seis plantillas del proyecto editables, Rise Fade instalado y Text+ básico Principal visibles; muestra final de 27 clips en una copia. Falta aceptación visual de Biglex.
- Los tres Text+ básicos usan nodos nativos con posiciones iniciales independientes; no añaden animación. Los títulos instalados y del proyecto conservan sus propias animaciones.
- Una frase demasiado larga puede desbordar el diseño de una plantilla. Repartirla entre capas o elegir otra; no hay autoajuste universal.
- Los registros de aplicación y deshacer se guardan por proyecto y secuencia. La fuente de subtítulos permanece intacta y visible; puedes ocultar su pista para revisar solo los textos generados.

Fuentes técnicas: documentación instalada `Support/Developer/Scripting/README.txt` y `Support/Developer/Fusion Templates/README.txt`, y [referencia de scripting de Blackmagic](https://documents.blackmagicdesign.com/UserManuals/Fusion8_Scripting_Guide.pdf). La compatibilidad final depende de Resolve 21 y de cada plantilla.

Los recursos generados del editor se guardan en `.davinci_flow/generated` dentro de la carpeta personal; conservarla junto con el proyecto. El botón Deshacer de la ventana principal usa el mismo registro editorial por secuencia.
