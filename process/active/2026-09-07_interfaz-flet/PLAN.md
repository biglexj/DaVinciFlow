# Interfaz Flet para DaVinci Flow

## Objetivo

Tras revisar la restauración lateral, Biglex señaló columnas y botones cortados, ausencia de desplazamiento horizontal, exceso de ancho lateral y limitaciones estéticas del prototipo Tkinter. Solicitó una apariencia elegante con bordes suaves y planteó el framework Flutter para Python, identificado como Flet. Continuar esa dirección conservando el motor editorial actual.

## Ejecución

1. Separar estado editorial de los controles Tk y reutilizar fuentes, propuesta, validación y escritura existentes.
2. Implementar una ventana Flet con lateral compacto, contraste legible, espaciado moderado y componentes compartidos. Editor, Plantillas, Biblioteca y Ajustes permanecen en la misma ventana.
3. Dar desplazamiento horizontal y vertical a tablas, envolver controles cuando falta ancho y mantener revisión/aplicación accesibles.
4. Conservar rutas, modelo, catálogo elegido y propuestas 1.0/1.1; proteger cambios pendientes y mostrar errores reales.
5. Validar acciones en una muestra de solo lectura de Resolve, persistencia y renderizado real. No aplicar a la secuencia del usuario automáticamente.

La interfaz Tkinter previa ha sido purgada por completo tras la consolidación exitosa de la interfaz moderna Flet, quedando Flet (`davinci_flow.ui.desktop`) como la única interfaz de usuario del sistema.

## Rendimiento y límites

Indexar nombres sin decodificar la biblioteca; trabajo lento fuera del hilo de interfaz y sin operaciones Resolve simultáneas. Flet añade un cliente Flutter; comprobar el comportamiento real y no afirmar menor consumo que Tk.

## Stack confirmado el 7 de septiembre

Biglex identificó PyPy y pidió Flet + uv + PyPy. La interfaz y el motor editorial usan PyPy 7.3.23 / Python 3.11.15. El código y la evidencia existente de esta instalación exigen CPython 3.13 para `fusionscript.dll`; mantenerlo como auxiliar efímero por operaciones cerradas, no como intérprete de la aplicación.

Flet 0.86.5 usa `sys.getrefcount` en el registro de servicios y PyPy carece de esa función. La versión final usa un selector propio con controles Flet: centrado, con listado local, ruta editable, validación de extensiones y confirmación de reemplazo. No registra servicios nativos ni altera `sys`. El cierre del cliente con `asyncio.subprocess` produjo un error CFFI de PyPy; usar el lanzador síncrono oficial de Flet con espera en un hilo. La adaptación requiere revisión al actualizar versiones.

Los diálogos se centran en la ventana y la ventana se centra en la pantalla al abrir. Se reutiliza el icono canónico; el ICO es un derivado técnico para Windows. Todos los accesos del menú y de consola deben apuntar a la misma ventana y reactivar la instancia existente.
