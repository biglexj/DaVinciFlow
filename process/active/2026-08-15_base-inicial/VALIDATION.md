# Validación — Base inicial de DaVinci Flow

## Comprobaciones automatizadas

- `python -m unittest discover -s tests -v`: 4 pruebas correctas.
- `python -m compileall -q src tests`: compilación sintáctica correcta.
- Regla `.agents/rules/base.md`: 2197 caracteres; permanece por debajo del límite de 12 000.

Las pruebas cubren orden y limpieza de subtítulos, ausencia de pistas, selección inválida y protección previa cuando Resolve está cerrado.

## Comprobación con DaVinci Resolve

Pendiente. Resolve no estaba ejecutándose durante esta validación.

El comando de diagnóstico terminó de forma controlada con el mensaje `DaVinci Resolve no está en ejecución`, sin cargar la biblioteca nativa ni modificar archivos o líneas de tiempo.

## Límites

Una prueba automatizada correcta demuestra la transformación de objetos simulados, pero no demuestra que los permisos, la conexión o el contenido real de Resolve funcionen en este equipo.
