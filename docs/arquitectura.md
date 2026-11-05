# Arquitectura y contratos de DaVinci Flow

- Estado: operativo
- Última actualización: 2026-11-03
- Alcance: mapa real del código, contratos exclusivos del producto y flujo de comandos.

Este documento es el mapa local del proyecto. Los estándares compartidos de estructura, calidad, procesos y comandos viven en la [Documentación Core](../../Docs/README.md) y se aplican desde allí; aquí solo se registra lo que es exclusivo de DaVinci Flow.

## 1. Dos raíces

| Raíz | Contenido | Regla |
|---|---|---|
| `src/davinci_flow/` | Motor headless: dominio, adaptadores de Resolve, IA, subtítulos, SFX, voz, temas y actualización. | No importa Flet ni ninguna interfaz. Es importable y comprobable sin ventana abierta. |
| `src-flet/` | Interfaz de escritorio: `app/` (shell y ciclo de vida), `features/` (vistas por dominio) y `shared/` (componentes transversales). | No habla con la API de Resolve: consume el motor. |

Entrada de escritorio: `src-flet/main.py`. Entrada de CLI: `python -m davinci_flow` (`src/davinci_flow/__main__.py`), que además expone `--install` (registra el lanzador en el menú de Resolve) y `--about`.

## 2. Mapa de módulos del motor

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
- Ejecución: `python -m davinci_flow.mcp_server` con `PYTHONPATH=src`.
- Protocolo declarado: `2025-06-18`; se admiten `2025-03-26` y `2024-11-05`.
- La propuesta editorial se publica siempre como propuesta: aplicarla exige `reviewed: true`.
- Una escritura que Resolve no confirma no se reintenta a ciegas.
- Catálogo de herramientas y registro en clientes: [MCP_SERVIDOR.md](MCP_SERVIDOR.md).

### 3.3 Temas y marca

Las plantillas visuales y las composiciones Fusion usan exclusivamente los temas oficiales **Ely** y **Aurora**, con validación estricta de paleta HEX y tipografía. Aurora se consulta como referencia selectiva: no se copian sus configuraciones particulares.

## 4. Flujo de comandos

Mise es la entrada principal. Detalle en el [README](../README.md) y en `scripts/mise-task.ts`.

| Tarea | Efecto | Publica |
|---|---|---|
| `mise setup` | `uv sync` y registro del lanzador en Resolve. | No |
| `mise dev` | Ejecuta la interfaz Flet con `PYTHONPATH=src;src-flet`. | No |
| `mise build` | Verifica sintaxis y genera los paquetes Python en `dist/`. | No |
| `mise check` | Sintaxis, importación de motor e interfaz y contratos de los scripts. | No |
| `mise test` | `unittest discover -s tests`. | No |
| `mise release` | Genera el instalador Inno Setup en `release/` y los paquetes Python en `dist/`. | No |
| `mise publish github --yes` | Crea el tag y la GitHub Release con el instalador y `SHA256SUMS.txt`. | Sí, de forma explícita |

- `--plan` muestra los comandos o el plan sin ejecutar, sin escribir y sin consultar la red.
- `--check` verifica requisitos locales y remotos en modo de solo lectura; no publica ni instala.
- Ninguna tarea acepta opciones que no implemente: una opción desconocida es un error.

### 4.1 Publicación

- GitHub Releases es la fuente de distribución. La sincronización de la ficha del producto en Aurora no está automatizada en este repositorio: se realiza por el canal administrativo descrito en el [estándar de release message web](../../Docs/global/releases/web-release-message-standard.md).
- La versión tiene una única fuente de verdad: `pyproject.toml`, reflejada en `src/davinci_flow/__init__.py`. Una versión publicada es inmutable.
- La release de Windows publica el instalador `.exe` y `SHA256SUMS.txt` bajo el mismo tag; los paquetes Python de `dist/` acompañan al tag como artefactos adicionales del repositorio.

### 4.2 Empaquetado

- Instalador: Inno Setup con la plantilla oficial Biglex Modern (`packaging/windows/setup.iss`, `identity.iss`, `version.iss`, `BiglexModernUI.iss`) y lanzador PyInstaller (`packaging/windows/launcher/`).
- `scripts/packaging/Build-Installer.ps1` genera el ejecutable de escritorio, valida las invariantes de empaquetado y compila el instalador en `release/`.
- Candado anti-binario obsoleto: si el ejecutable empaquetado es más viejo que `src/`, `assets/`, `packaging/windows/launcher/` o `pyproject.toml`, la compilación falla. Solo `-ForceStale` lo permite, y es únicamente para depurar.

## 5. Proceso y validación

- Los procesos viven en `process/active/YYYY-MM-DD_objetivo/` con `PLAN.md`, `TASKS.md`, `VALIDATION.md` y `APPROVAL.md`.
- La evidencia se registra en `VALIDATION.md`: una prueba unitaria no sustituye la verificación dentro de DaVinci Resolve.
- `ROADMAP.md` conserva los pendientes generales e informa de la tarea de refactorización que exige todo archivo que supere el límite de tamaño local.
