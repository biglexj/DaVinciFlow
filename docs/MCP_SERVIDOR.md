# DaVinci Flow como herramienta MCP

DaVinci Flow publica sus operaciones como un servidor **MCP por stdio**, para que
cualquier agente pueda operatedor sin abrir la interfaz gráfica. Es el paso que
convierte la herramienta en un producto: no solo coloca subtítulos, sino que expone
efectos, voz, autocorrección y consulta de la API de Resolve.

## Arrancar el servidor

```bash
# Desde la raíz del repositorio, con el entorno del proyecto
python -m davinci_flow.mcp_server
```

El servidor habla JSON-RPC 2.0 sobre entrada y salida estándar, una línea por
mensaje. Es el mismo protocolo que usa el MCP oficial de Resolve, así que cualquier
cliente MCP puede registrarlo como un servidor más.

## Registro en un cliente MCP

```json
{
  "mcpServers": {
    "davinci-flow": {
      "command": "python",
      "args": ["-m", "davinci_flow.mcp_server"],
      "cwd": "D:/Proyectos/biglexj/DaVinciFlow",
      "env": { "PYTHONPATH": "D:/Proyectos/biglexj/DaVinciFlow/src" }
    }
  }
}
```

En el runtime local de Mavis se registra con `mavis mcp create` (transport `stdio`,
comando `python`, argumentos `["-m", "davinci_flow.mcp_server"]` y el `cwd` del
repositorio).

## Herramientas publicadas

| Herramienta | Qué hace | Escribe en Resolve |
|---|---|---|
| `davinciflow_status` | Transporte, proveedor, modelo y credenciales disponibles | No |
| `davinciflow_capture` | Captura los subtítulos de la línea de tiempo activa | No |
| `davinciflow_templates` | Catálogo de plantillas y títulos del Media Pool | No |
| `davinciflow_propose` | Genera una propuesta editorial con el proveedor activo | No |
| `davinciflow_apply` | Aplica una propuesta **ya revisada** | Sí |
| `davinciflow_undo` | Deshace la última aplicación registrada | Sí |
| `davinciflow_insert_native_title` | Inserta un título nativo (`Text+`, `Fade On`…) | Sí |
| `davinciflow_create_fusion_effect` | Crea un efecto Fusion editable y lo inserta | Sí |
| `davinciflow_synthesize_speech` | Genera locución con Minimax y sus subtítulos | No (escribe en disco) |
| `davinciflow_autocorrect` | Corrige subtítulos y devuelve el diff por etapa | No |
| `davinciflow_write_subtitles` | Escribe en la pista nativa de subtítulos | Sí |
| `davinciflow_scripting_api_search` | Busca en la API de scripting vía MCP oficial | No |
| `davinciflow_scripting_docs` | Lee la documentación de la API vía MCP oficial | No |

## Garantías heredadas del puente de Resolve

- **La propuesta no se aplica sola.** `davinciflow_propose` deja el resultado en disco
  con su ruta; `davinciflow_apply` exige `reviewed: true`.
- **Una escritura fallida no se reintenta a ciegas.** Si Resolve no confirma el
  resultado, la herramienta informa del estado y no repite la operación.
- **Las credenciales no viajan en los datos.** Se resuelven en el servidor y solo se
  usan en la cabecera de autenticación del proveedor.
- **Los efectos quedan editables.** Las composiciones se insertan como objetos Fusion
  (nunca renderizadas) y los títulos nativos se insertan con
  `InsertFusionTitleIntoTimeline`, de modo que siguen editables en el Inspector.

## Ejemplo de sesión

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"davinciflow_status","arguments":{}}}
```

## Efectos Fusion disponibles

`davinciflow_create_fusion_effect` acepta:

- `text`: contenido del nodo `Text+`.
- `role`: `main`, `context` o `accent` (tema Ely/Aurora).
- `animation_preset`: `none`, `pop_bounce`, `slide_up`, `fade_smooth`, `kinetic_pulse`
  o `typewriter`.
- `position_x` / `position_y`: posición normalizada (0 a 1).
- `glow`: intensidad del brillo (0 a 1). Inserta un nodo `Glow` entre la
  transformación y la salida.
- `start_frame`, `duration_frames`, `track_index`: colocación en la línea de tiempo.
