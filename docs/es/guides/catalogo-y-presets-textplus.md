# Biblioteca de títulos y presets Text+

## Objetivo del producto

DaVinci Flow ayuda a convertir una transcripción en una edición revisable mediante títulos nativos editables. El flujo es: **biblioteca visual → preset de plantillas → propuesta editorial → revisión → aplicación**. Luna Fetch aporta medios al Media Pool como herramienta complementaria.

Text+ es el título nativo de Resolve. Utiliza Fusion internamente, pero el resultado debe conservar el Inspector de título; un vídeo portador con una composición importada no cumple ese criterio.

## Explorar y elegir

Al abrir **Plantillas**, se leen automáticamente los títulos instalados y se muestran **Todas las plantillas**. La galería utiliza cuatro columnas cuando el ancho disponible alcanza 960 px y reduce las columnas en ventanas menores; el desplazamiento queda dentro del catálogo. **Con animación** filtra los vídeos originales y **Con miniatura** las imágenes. **Leer instalados** actualiza el inventario manualmente.

El catálogo consulta archivos SETTING, paquetes DRFX y títulos DRB de las bibliotecas locales, si existen en este equipo. **Añadir carpeta** permite consultar otras bibliotecas. **Leer proyecto** incorpora los títulos reconocidos en el Media Pool del proyecto activo; esos clips no aportan por sí solos el vídeo de muestra del archivo instalado.

Las copias propias llevan la marca **DaVinci Flow**; las referencias animadas conservan su procedencia y se distinguen de esas copias. Los prefijos técnicos del proveedor no se usan como nombres visibles. Se conservan los localizadores originales.

**Ver animación** reproduce el vídeo original y **Ver captura** abre la imagen real. Cuando solo existe un vídeo, se obtiene un fotograma con FFmpeg. Las capturas se conservan en caché según la identidad y huella del título. Si falta muestra para un título nativo o SETTING, la captura requiere el proyecto de producción acordado; se restaura el contexto previo al terminar. Las bases DRB, Media Pool y DRFX sin muestra requieren una secuencia preparada: no se insertan automáticamente para obtener una captura. Un fallo deja la tarjeta con captura pendiente y no detiene las demás muestras disponibles.

El destino compartido es **Contenidos / Biglex J Producciones / Titulos / DF_Validacion_TextPlus_20261109**, según la [regla de producción Core](../../../../Docs/guides/cross-platform/editors/davinci-resolve-produccion.md). El vídeo original de una referencia no acredita el aspecto de su copia adaptada.

Las muestras de terceros siguen en su instalación original. No se redistribuyen en DaVinci Flow. Las imágenes de archivos DRFX se extraen individualmente a la caché del usuario.

## Guardar una selección

Abre **Mis presets**, selecciona las plantillas, escribe un nombre y pulsa **Guardar selección**. **Usar preset** recupera esa selección para la próxima propuesta. El preset conserva los descriptores y huellas; no crea una nueva animación ni modifica el original.

La primera colección editorial debe prepararse y revisarse visualmente antes de tomarla como referencia de calidad. Sus variantes de una, dos y tres capas, y sus adaptaciones horizontal/vertical, son trabajo de diseño pendiente; los packs básicos existentes no representan esa aceptación.

## Consulta y aplicación

- **DRB y Media Pool:** el motor copia el título y comprueba posición, pista, duración, identidad y texto. Conserva tipografía, posición y animación de la plantilla; no fuerza todas las plantillas a la misma geometría.
- **SETTING y DRFX:** disponibles para consulta y selección. Su aplicación editorial exige primero una base nativa preparada. El motor lo indica en el preflight, antes de crear pistas o clips.
- No se sustituye una inserción fallida por un vídeo portador. La aplicación real de los nuevos DRB y la accesibilidad de su Inspector todavía deben verificarse de extremo a extremo en Resolve.

## Versión instalada y desarrollo

El acceso de Resolve prioriza `DaVinciFlow.exe` instalado. Si existe esa instalación y su lanzador, la preparación desde el repositorio conserva el lanzador existente.

El ejecutable instalado mantiene sus datos en `~/.davinci_flow`. Cada checkout de desarrollo utiliza `~/.davinci_flow/development/<identificador-del-checkout>` para credenciales, preferencias, presets, voz, caché y registros. No se copian automáticamente las claves o preferencias de la instalación estable. La ventana identifica el modo **Desarrollo**.

Las llamadas por MCP restauran tanto las rutas Python como los módulos de DaVinci Flow previamente cargados. Esto evita que una operación de un checkout deje su versión del paquete cargada para otra instalación. Compartir Resolve permite que ambas versiones actúen sobre el mismo proyecto: una prueba de desarrollo debe usar una secuencia de prueba y coordinación explícita si hay otra sesión trabajando.
