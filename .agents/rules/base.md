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
- Stack activo: Rust con GPUI y MCP oficial de Resolve. Los servicios pendientes de migración usan el adaptador CPython 3.13 en `compat/python`.
- El entorno `.venv` de compatibilidad se prepara con `mise setup`.
- Las plantillas visuales usan exclusivamente los temas oficiales Ely y Aurora, con validación estricta de paleta y tipografía.

## 3. Arquitectura local

Mapa vigente y contratos por módulo: [docs/arquitectura.md](../../docs/arquitectura.md). Decisiones propias:

- El código activo está en `src/`. Las vistas y acciones de GPUI se organizan por función en `src/app/`.
- Los accesos a Resolve se concentran en `src/resolve_mcp.rs`, `src/resolve_scripts/` y los adaptadores de `compat/python/`.
- No se crean módulos para capacidades todavía inactivas.
- Límite de tamaño: evitar archivos de más de 900 líneas; 1200 es el máximo excepcional (ver [base de Python](../../../Docs/stacks/python/python-baseline.md)). Superar 1200 líneas convierte el archivo en deuda técnica activa y exige una tarea de refactorización en `ROADMAP.md`.
- Temporales: `temp/` (borradores), `scratch/` (mantenimiento) y `test/` (pruebas temporales), en la raíz. Las pruebas de Rust viven junto a sus módulos. Las del puente están en `compat/python/tests/`.

## 4. Flujo de trabajo local

El ciclo y sus fases se rigen por el [flujo de procesos](../../../Docs/global/documentation/process-workflow.md). Decisiones propias:

- Cada trabajo planificado vive en `process/active/YYYY-MM-DD_objetivo/`; `ROADMAP.md` conserva los pendientes generales. No existe `TASKS.md` en la raíz.
- La evidencia real se registra en `VALIDATION.md`. Una prueba unitaria no sustituye la verificación dentro de DaVinci Resolve.
- No se anuncia una versión como publicada sin comprobar el remoto.

## 5. Comandos (Mise)

`mise dev` ejecuta GPUI desde el checkout actual. `mise build`, `mise check` y `mise test` trabajan con el proyecto Rust. `mise setup` prepara el adaptador de compatibilidad. Las tareas admiten `--plan`.

Flet 1.0.0 está descontinuado en la rama `v-python`, con su propio `mise dev`.

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

- La versión de GPUI se declara en `Cargo.toml`. La distribución nativa de Windows sigue pendiente.
- El código del instalador anterior quedó en el archivo de Flet 1.0.0. El desarrollo continúa en `main`.

## 9. Soporte oficial (local)

El diálogo «Acerca de» y su insignia en la barra lateral implementan la [base de soporte oficial](../../../Docs/features/official-support/official-support-baseline.md) con los cuatro enlaces canónicos (donaciones, Buy Me a Coffee, feedback y GitHub). No se sustituyen por destinos propios.

## 10. Referencias locales

- [core_profile.md](core_profile.md) — perfil de aplicabilidad de Core.
- [folder_structure.md](folder_structure.md) — mapa de carpetas vigente.
- [docs/arquitectura.md](../../docs/arquitectura.md) — arquitectura, contratos y mapa de módulos.
- [docs/MCP_SERVIDOR.md](../../docs/MCP_SERVIDOR.md) — servidor MCP propio.
- [docs/es/guides/](../../docs/es/guides/) — guías funcionales del producto.
- `AI_MODELS.md`, `ROADMAP.md`, `RELEASE_NOTES.md` y `RELEASE_MESSAGE.md` son registros locales (producto, historial y notas); no son reglas normativas.
