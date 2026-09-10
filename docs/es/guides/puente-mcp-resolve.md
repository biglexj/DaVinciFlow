# Puente oficial con DaVinci Resolve Studio 21.1

El editor de DaVinci Flow utiliza el MCP que Blackmagic distribuye con Resolve Studio 21.1. No necesita conectar una cuenta de Claude/ChatGPT, instalar otro servidor MCP ni cambiar la configuración de Codex: DaVinci Flow actúa como cliente local.

## Recorrido

Interfaz Flet → controlador editorial → puente MCP → Python integrado de Resolve → operaciones editoriales existentes → resultado JSON.

Las cuatro operaciones integradas son capturar subtítulos y montaje, leer las plantillas del Media Pool, aplicar una propuesta revisada y deshacer la ejecución de la secuencia actual. Los comandos clásicos de la CLI (`--plan`, `--generate`, etc.) siguen utilizando el adaptador de scripting anterior.

El MCP cambia el transporte. La LLM, la revisión por bloque, las plantillas, la huella de la secuencia y los registros de reversión mantienen su responsabilidad. No se ejecuta texto producido por la LLM como código.

## Configuración

Por defecto, `DAVINCIFLOW_RESOLVE_TRANSPORT=auto` selecciona el MCP si encuentra el ejecutable. En Windows se comprueba la ruta habitual y la asociación oficial `.drp` para instalaciones en otras unidades.

| Variable | Valores y efecto |
| --- | --- |
| `DAVINCIFLOW_RESOLVE_TRANSPORT` | `auto` (predeterminado), `mcp` (obligatorio) o `legacy` (auxiliar anterior). |
| `DAVINCIFLOW_RESOLVE_MCP` | Ruta opcional al ejecutable oficial `ResolveMCP.exe`. Una ruta explícita inválida produce un error. |
| `DAVINCIFLOW_RESOLVE_PYTHON` | Intérprete CPython 3.13 x64 del transporte `legacy`. |

En `auto` solo se usa el transporte anterior si el ejecutable MCP no existe. Un error, cierre, timeout o rechazo del MCP no provoca un segundo intento por el auxiliar. Reinicia DaVinci Flow para cargar cambios de código o entorno en una instancia ya abierta.

Para consultar la conexión desde PowerShell en el repositorio:

```powershell
$env:PYTHONPATH = "$PWD\src"
@'
from davinci_flow.editorial.resolve_bridge import connection_status
print(connection_status())
'@ | .\.venv\Scripts\python.exe -
```

La respuesta MCP incluye `transport`, ruta del ejecutable, servidor, versión y estado `running`. La respuesta `legacy` identifica el intérprete; por sí sola no confirma un proyecto abierto.

## Acceso y límites

- Se inicia un proceso MCP local por operación y se cierra al terminar. No se abre un puerto de red y no hay conexiones nuevas a proveedores de IA para capturar/aplicar.
- Se usa `run_script_unsafe` porque importar el paquete local, leer propuestas y plantillas Fusion y guardar registros requiere acceso al sistema de archivos. El script es fijo, inyecta la sesión proporcionada por Resolve y recibe parámetros como JSON. No acepta código libre desde la interfaz ni desde una propuesta.
- El Python de la aplicación sigue siendo CPython 3.13. El recorrido MCP probado usa el Python 3.14 integrado de Resolve; no exige instalarlo por separado.
- El servidor admite hasta 60 segundos por script. DaVinci Flow espera hasta 75 segundos por la respuesta. Una escritura sin respuesta válida queda explícitamente sin confirmar: no se reintenta ni cambia de transporte. Comprueba el montaje y el registro antes de repetir o deshacer. No se ha validado una generación extensa superior a ese límite.
- Los identificadores nuevos de clips usan `DF__...`: Resolve 21.1 rechaza `:` en `SetName`. Se reconocen los nombres anteriores `DF::...` para reutilización y reversión.
- Las transiciones de 21.1 forman parte de la huella con identidad, nombre y tiempos, sin inventar offsets de origen. Un clip de medios sin offsets válidos bloquea la captura.

## Evidencia

El 2026-09-10, el controlador editorial capturó 72 subtítulos y 65 elementos de montaje (15 transiciones) de una sesión real. En un duplicado temporal, el flujo aplicó un título Fusion, confirmó texto, posición y duración, lo reaplicó sin duplicación y lo deshizo. Se retiraron la secuencia/carpeta temporales y se comprobó la misma huella del montaje original.

Esto valida el recorrido técnico de una muestra; no equivale a aceptación visual/auditiva de una generación completa ni a una versión publicada. Consulta el [proceso y la evidencia](../../../process/active/2026-09-10_puente-mcp-oficial/VALIDATION.md).
