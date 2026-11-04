---
trigger: always_on
---

# DaVinci Flow — entrada de instrucciones

> Puente local hacia la [Documentación Core](../../../Docs/README.md). Los estándares compartidos se aplican desde su fuente canónica; este archivo conserva solo los contratos y las decisiones exclusivos de DaVinci Flow. Ante una contradicción, manda la implementación vigente: se comprueba el código y se resuelve de forma explícita, sin copiar reglas de Core aquí.

## 1. Documentación Core aplicable

Seleccionar únicamente los módulos que correspondan al encargo:

| Ámbito | Fuente canónica |
|---|---|
| Reglas de trabajo del agente, tamaño de las reglas y commits de resguardo | [Reglas de trabajo del agente](../../../Docs/global/documentation/agent-working-rules.md) |
| Tono de las respuestas (Scientific Elegant) | [Estilo de comunicación](../../../Docs/global/agents/communication-style.md) |
| Calidad y entrega proporcionales | [Base de calidad](../../../Docs/global/quality/quality-baseline.md) |
| Procesos según alcance (`PLAN`/`TASKS`/`VALIDATION`/`APPROVAL`) | [Flujo de procesos](../../../Docs/global/documentation/process-workflow.md) |
| Gobernanza documental y promoción a Core | [Gobernanza](../../../Docs/global/documentation/documentation-governance.md) · [Promoción](../../../Docs/global/documentation/core-promotion-workflow.md) |
| Arquitectura y organización de carpetas | [Base de arquitectura](../../../Docs/global/architecture/architecture-baseline.md) · [Organización de proyectos](../../../Docs/global/architecture/project-structure.md) |
| Stack Python (dos raíces, `uv`, límites de archivo) | [Base de Python](../../../Docs/stacks/python/python-baseline.md) |
| Comandos y scripts | [Comandos mediante Mise](../../../Docs/global/architecture/mise-command-standard.md) · [Scripts y alias](../../../Docs/global/architecture/command-scripts-standard.md) |
| Diseño y textos de interfaz | [Lenguaje de diseño](../../../Docs/global/design/design_system.md) · [Textos de interfaz](../../../Docs/global/design/interface-writing.md) |
| Lanzamientos | [Base de lanzamientos](../../../Docs/global/releases/release-baseline.md) · [Protocolo oficial](../../../Docs/global/releases/protocolo_lanzamiento_actualizacion.md) · [Release Message web](../../../Docs/global/releases/web-release-message-standard.md) |
| Modelos de IA | [Modelos de IA](../../../Docs/features/ai-models/README.md) |
| «Acerca de» y apoyo oficial | [Soporte oficial](../../../Docs/features/official-support/official-support-baseline.md) |
| Instaladores | [Instaladores](../../../Docs/features/installer/README.md) · [Instalación en Windows](../../../Docs/platforms/windows/installer.md) |
| Diagnósticos reutilizables | [Problemas conocidos](../../../Docs/troubleshooting/README.md) |

Reglas locales siempre activas: [perfil Core](core_profile.md) · [mapa de carpetas](folder_structure.md).

## 2. Identidad y alcance (local)

- Producto: automatización para DaVinci Resolve 21; no es una aplicación independiente.
- Autor: biglexj. Licencia: MIT.
- Stack activo: CPython 3.13 de 64 bits, Flet 0.86.5, API de scripting de DaVinci Resolve 21 y servidor MCP propio sobre stdio.
- Entorno único `.venv` gestionado con `uv`; no se mantienen entornos virtuales paralelos.
- Las plantillas visuales usan exclusivamente los temas oficiales Ely y Aurora, con validación estricta de paleta y tipografía.

## 3. Arquitectura local

Mapa vigente y contratos por módulo: [docs/arquitectura.md](../../docs/arquitectura.md). Decisiones propias:

- Dos raíces: `src/davinci_flow/` (motor headless, sin dependencias de interfaz) y `src-flet/` (interfaz Flet: `app/`, `features/`, `shared/`).
- La API de Resolve solo se alcanza desde adaptadores (`src/davinci_flow/resolve/`, `editorial/resolve_bridge.py`, `editorial/mcp_bridge.py`); la lógica reutilizable no depende de la interfaz.
- No se crean módulos para capacidades todavía inactivas.
- Límite de tamaño: evitar archivos de más de 900 líneas; 1200 es el máximo excepcional (ver [base de Python](../../../Docs/stacks/python/python-baseline.md)). Superar 1200 líneas convierte el archivo en deuda técnica activa y exige una tarea de refactorización en `ROADMAP.md`.
- Temporales: `temp/` (borradores), `scratch/` (mantenimiento) y `test/` (pruebas temporales), en la raíz. Las pruebas permanentes viven en `tests/`.

## 4. Flujo de trabajo local

El ciclo y sus fases se rigen por el [flujo de procesos](../../../Docs/global/documentation/process-workflow.md). Decisiones propias:

- Cada trabajo planificado vive en `process/active/YYYY-MM-DD_objetivo/`; `ROADMAP.md` conserva los pendientes generales. No existe `TASKS.md` en la raíz.
- La evidencia real se registra en `VALIDATION.md`. Una prueba unitaria no sustituye la verificación dentro de DaVinci Resolve.
- No se anuncia una versión como publicada sin comprobar el remoto.

## 5. Comandos (Mise)

Mise es la entrada principal de comandos: [estándar de comandos](../../../Docs/global/architecture/mise-command-standard.md). Tareas realmente expuestas por el proyecto:

| Tarea | Efecto |
|---|---|
| `mise setup` | Prepara `.venv` con `uv` e instala el lanzador de Resolve. |
| `mise dev` | Ejecuta la interfaz Flet en desarrollo. |
| `mise build` | Verifica sintaxis y genera los paquetes Python en `dist/`, sin instalador. |
| `mise check` | Comprueba sintaxis, importación y contratos de los scripts, sin artefactos. |
| `mise test` | Ejecuta la suite unitaria. |
| `mise release` | Prepara artefactos locales (instalador Windows y paquetes Python). No publica. |
| `mise publish` | Publicación explícita en GitHub Releases; exige autorización explícita. |

`--plan` no ejecuta, no escribe y no consulta la red. `--check` solo verifica. Detalle operativo y ejemplos: [README](../../README.md) y `scripts/mise-task.ts`. Scripts de arranque directo: `scripts/setup-desktop.ps1` y `scripts/start-desktop.ps1`.

## 6. IA y credenciales (local)

- El código y la configuración ejecutable son la fuente de verdad del modelo. `AI_MODELS.md` es el registro local explicativo: [modelos de IA](../../../Docs/features/ai-models/README.md).
- Los proveedores se consumen tras el contrato `TextProvider`; no se fija un catálogo de modelos actuales en las reglas.
- No se sustituye silenciosamente el análisis del LLM por reglas locales, ni se cambia de modelo o proveedor sin registrar compatibilidad y validación.
- Credenciales: `~/.davinci_flow/config.json` (clave por proveedor), preferencias en `~/.davinci_flow/editorial_preferences.json` y voz en `~/.davinci_flow/voice/`. Variables admitidas: `GEMINI_API_KEY` y `MINIMAX_API_KEY`. Las claves no entran en el repositorio, los registros ni la interfaz visible.

## 7. Contrato MCP propio (local)

- Transporte: JSON-RPC 2.0 sobre stdio (`python -m davinci_flow.mcp_server`). No hay servidor de red ni puertos abiertos.
- Protocolo declarado: `2025-06-18`; se admiten `2025-03-26` y `2024-11-05`.
- La propuesta editorial exige `reviewed: true` antes de aplicarse y una escritura que Resolve no confirma no se reintenta a ciegas.
- Catálogo de herramientas y registro en clientes: [docs/MCP_SERVIDOR.md](../../docs/MCP_SERVIDOR.md).

## 8. Empaquetado y publicación (local)

- Instalador: Inno Setup con la plantilla oficial Biglex Modern, generado en `release/`; reglas en [instaladores](../../../Docs/features/installer/README.md) y [Windows](../../../Docs/platforms/windows/installer.md).
- El empaquetado conserva el candado anti-binario obsoleto: el artefacto se compara con `src/`, `assets/` y `packaging/` antes de empaquetar y la compilación falla si está atrasado ([diagnóstico](../../../Docs/troubleshooting/tools/inno-stale-binary-packaging.md)).
- `release` prepara y no publica; `publish` publica en GitHub Releases de forma explícita y requiere autorización. La sincronización con la ficha de Aurora no está automatizada en este proyecto: se realiza por el canal administrativo descrito en el [Release Message web](../../../Docs/global/releases/web-release-message-standard.md).
- La versión tiene una única fuente de verdad: `pyproject.toml`, reflejada en `src/davinci_flow/__init__.py`.

## 9. Soporte oficial (local)

El diálogo «Acerca de» y su insignia en la barra lateral implementan la [base de soporte oficial](../../../Docs/features/official-support/official-support-baseline.md) con los cuatro enlaces canónicos (donaciones, Buy Me a Coffee, feedback y GitHub). No se sustituyen por destinos propios.

## 10. Referencias locales

- [core_profile.md](core_profile.md) — perfil de aplicabilidad de Core.
- [folder_structure.md](folder_structure.md) — mapa de carpetas vigente.
- [docs/arquitectura.md](../../docs/arquitectura.md) — arquitectura, contratos y mapa de módulos.
- [docs/MCP_SERVIDOR.md](../../docs/MCP_SERVIDOR.md) — servidor MCP propio.
- [docs/es/guides/](../../docs/es/guides/) — guías funcionales del producto.
- `AI_MODELS.md`, `ROADMAP.md`, `RELEASE_NOTES.md` y `RELEASE_MESSAGE.md` son registros locales (producto, historial y notas); no son reglas normativas.
