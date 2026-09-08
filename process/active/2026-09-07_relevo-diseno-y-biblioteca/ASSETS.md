# División de assets y rutas

## Biblioteca real

Raíz comprobada por lectura: `D:\Vídeos\Assets`. `D:\Videos\Assets` es una ruta diferente y no existe. Mantener las tildes al guardar, restaurar e indexar rutas.

El inventario del 7 de septiembre devuelve 1849 imágenes/vídeos, 1318 archivos de audio y 4 documentos. No se han movido, renombrado ni analizado audiovisualmente. La clasificación por extensión no separa música de efectos.

| Categoría del producto | Clave actual | Origen o propuesta | Uso |
|---|---|---|---|
| Visuals / B-rolls | `visuals` | `D:\Vídeos\Assets`; existen subcarpetas como 9.16, Anime, Fondo Video e Imagen-Fondo | Imágenes y vídeos de apoyo; filtros de tipo y orientación |
| Efectos de sonido | `sfx` | `D:\Vídeos\Assets\Audio Efects` existe | Pops, impactos, whooshes y otros efectos; revisar antes de clasificar por función |
| Música | `music` | `D:\Vídeos\Assets\Audio Music` existe | Fondos musicales independientes de los efectos |
| Títulos / Fusion | `titles` | Elegir ruta externa si corresponde; los títulos instalados y del Media Pool se leen por sus propios adaptadores | Plantillas de texto y animación |
| Textos / Documentos | `documents` | Elegir carpeta concreta; el escaneo general detectó 4 documentos | Guion, contexto y referencias; hoy solo se comparte su nombre |

La separación inicial es lógica: cada categoría apunta a su carpeta actual. No hace falta reorganizar físicamente toda la biblioteca para empezar. Una migración física requeriría revisar las referencias existentes de Resolve y constituye otro trabajo.

## Contrato disponible

`assets/library.py` produce ID estable, categoría, nombre relativo y ruta local. El contexto enviado a la LLM contiene solo ID, nombre y categoría de hasta 80 recursos elegidos. El límite del inventario es 2000 archivos por categoría. `editorial/preferences.py` persiste las rutas y selecciones en `.davinci_flow/editorial_preferences.json`.

Los nombres sirven como contexto débil; no acreditan comprensión visual o sonora. Actualmente `resource_id` y `visual_note` son una recomendación única y una nota por bloque, sin aplicación multimedia. Este contrato no basta para varios recursos simultáneos ni para las dos pistas SFX: extenderlo en fase 2/3 con compatibilidad explícita.

## Trabajo pendiente de integración

1. Corregir la ruta activa a la carpeta real y conservarla al reiniciar. Precargar las dos carpetas de audio verificadas cuando se ejecute este bloque.
2. Separar música y SFX por raíz/categoría, no por `.wav` o `.mp3`. Manejar rutas solapadas para que un archivo no aparezca como música y efecto involuntariamente; permitir una asignación múltiple solo cuando el usuario la elija.
3. Conservar los IDs y la selección al filtrar/reindexar. Distinguir recurso eliminado, raíz desconectada, error de permisos y selección vacía. No borrar silenciosamente la selección porque una unidad no está conectada.
4. Mostrar los diagnósticos y conteos por categoría. Excluir temporales, carpetas ocultas y enlaces que lleven fuera del inventario.
5. Unir la carpeta de títulos configurada con el catálogo de Plantillas. Mantener separadas las procedencias instaladas y Media Pool; una ruta por sí sola no selecciona títulos para la LLM.
6. Mantener los documentos como catálogo de nombres mientras no se implemente lectura explícita. Si se añade lectura, hacerla acotada y visible; no enviar una carpeta entera de documentos automáticamente.
7. Preparar metadatos y previsualizaciones bajo demanda para fases 2/3; evitar decodificar toda la biblioteca al abrir la aplicación.

## Aceptación

Cada categoría puede indexarse y recuperar su ruta después de reiniciar; música y efectos están separados; los archivos originales conservan nombre y ubicación. El usuario puede saber exactamente qué selección verá la LLM. Un recurso ausente no se transforma en una inserción ficticia ni se confunde con que la biblioteca está vacía.
