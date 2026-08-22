# Validación — Base inicial de DaVinci Flow

## Comprobaciones automatizadas

- Fecha: 21 de agosto de 2026.
- `Python 3.13 -m unittest discover -s tests -q`: 95 pruebas correctas.
- `python -m compileall -q src tests`: compilación sintáctica correcta.

## Comprobación real con DaVinci Resolve 21

- Proyecto: `Crear proyecto 1`.
- Línea de tiempo: `Timeline 1`.
- Pista nativa de subtítulos: 1.
- Resultado: 369 subtítulos leídos en orden desde la API real.
- Contexto detectado: 4 pistas de vídeo, 2 de audio y 1 de subtítulos.
- La lectura y planificación no modificaron la línea de tiempo.

## Hallazgo de compatibilidad

En este equipo, cargar `fusionscript.dll` desde Python 3.11 o 3.12 provoca una violación de acceso nativa. Python 3.13 carga la biblioteca y obtiene la sesión correctamente. El cliente ahora detiene runtimes externos incompatibles antes de cargar la DLL.

## Límite

La conexión y lectura están verificadas. La aprobación visual de la interfaz y de los títulos pertenece al proceso de subtítulos dinámicos y SFX.
