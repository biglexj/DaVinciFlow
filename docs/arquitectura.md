# Arquitectura y contratos de DaVinci Flow

- Estado: operativo
- Última actualización: 2026-11-22
- Alcance: mapa real del código, contratos exclusivos del producto y flujo de comandos.

Este documento es el mapa local del proyecto. Los estándares compartidos de estructura, calidad, procesos y comandos viven en la [Documentación Core](../../Docs/README.md) y se aplican desde allí; aquí solo se registra lo que es exclusivo de DaVinci Flow.

## 1. Organización

La aplicación activa es Rust + GPUI en `main` y se ejecuta con `mise dev`. El código de la ventana se organiza por función en `src/app/` y consume los módulos del motor en `src/`.

`src/resolve_scripts/` contiene las llamadas que ejecuta el MCP oficial dentro de Resolve. `compat/python/bridge/` conserva los adaptadores de las operaciones pendientes de migrar y `compat/python/src/davinci_flow/` el motor que esos adaptadores invocan. `mise setup` prepara el entorno local de compatibilidad.

Flet 1.0.0 está descontinuado en la rama `v-python`. Su `mise dev` utiliza el propio checkout de esa rama.

## 2. Mapa del motor de compatibilidad

| Módulo | Responsabilidad | Contrato de salida |
|---|---|---|
| `application.py` | Coordina los casos de uso del producto. | Orquesta; no habla con Resolve directamente. |
| `editorial/` | Propuesta editorial, revisión, preferencias y escritura de la propuesta revisada. | `planner.propose()` devuelve una propuesta sin aplicar; aplicar exige `reviewed: true`. |
| `resolve/` | Adaptadores exclusivos de la API de DaVinci Resolve 21. | Ninguna otra capa importa el SDK de Resolve. |
| `editorial/resolve_bridge.py`, `editorial/mcp_bridge.py` | Puentes hacia Resolve: DLL auxiliar o MCP oficial de Blackmagic. | Puerto estable hacia `resolve/`. |
| `ai/` | Contrato `TextProvider`, adaptadores Gemini y Minimax, reintentos y credenciales. | La selección de proveedor y modelo es externa al motor editorial. |
| `subtitles/` | Modelo de cues, normalización, clasificación en capas y autocorrección por etapas. | Salida auditable con diff por subtítulo. |
| `generation/` | Plan de generación versionado, plantillas Fusion, portadoras y registro de clips. | Un mismo plan reutiliza clips identificados. |
| `sfx/` | Catálogo auditable y materialización de WAV procedurales. | Control de densidad y marca `[SFX_OFF]`. |
| `voice/` | Locución sintética y subtítulos alineados a la propia voz. | Salida en `~/.davinci_flow/voice/`. |
| `themes/` | Tokens de los temas oficiales Ely y Aurora. | Validación estricta de paleta y tipografía. |
| `updater/` | Comprobación de actualizaciones y sanitización de notas. | Markdown limpio, sin rutas ni ruido interno. |
| `mcp_server.py` | Publica las operaciones del producto como herramientas MCP. | JSON-RPC 2.0 sobre stdio. |

## 3. Contratos exclusivos del producto

### 3.1 Rutas y configuración del usuario

| Dato | Ruta |
|---|---|
| Credenciales de proveedores | `~/.davinci_flow/config.json` (clave por proveedor) |
| Preferencias editoriales (proveedor, modelo, opciones) | `~/.davinci_flow/editorial_preferences.json` |
| Locución generada | `~/.davinci_flow/voice/` |

Las claves nunca se escriben en el repositorio, los registros ni la interfaz visible. Variables de entorno admitidas: `GEMINI_API_KEY` y `MINIMAX_API_KEY`.

### 3.2 Contrato MCP propio

- Transporte: JSON-RPC 2.0 sobre stdio. Sin servidor de red, sin puertos abiertos.
- Ejecución: `python -m davinci_flow.mcp_server` con `.venv/Scripts/python.exe` después de `mise setup`.
- Protocolo declarado: `2025-06-18`; se admiten `2025-03-26` y `2024-11-05`.
- La propuesta editorial se publica siempre como propuesta: aplicarla exige `reviewed: true`.
- Una escritura que Resolve no confirma no se reintenta a ciegas.
- Catálogo de herramientas y registro en clientes: [MCP_SERVIDOR.md](MCP_SERVIDOR.md).

### 3.3 Temas y marca

Las plantillas visuales y las composiciones Fusion usan exclusivamente los temas oficiales **Ely** y **Aurora**, con validación estricta de paleta HEX y tipografía. Aurora se consulta como referencia selectiva: no se copian sus configuraciones particulares.

## 4. Flujo de comandos

Mise abre, compila y verifica la aplicación Rust con `dev`, `build`, `check` y `test`. Consulta las tareas y sus opciones en el [README](../README.md). La versión de GPUI se declara en `Cargo.toml`. El instalador nativo queda pendiente.
