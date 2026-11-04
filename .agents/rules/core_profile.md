---
trigger: always_on
---

# Perfil de Documentación Core — DaVinci Flow

- Última revisión: 2026-11-03
- Tipo principal: automatización para aplicación de escritorio de Windows
- Plataformas: Windows 11 y DaVinci Resolve 21
- Stack: CPython 3.13 de 64 bits, Flet 0.86.5, API de scripting de DaVinci Resolve 21 y `unittest`
- Funciones activas: conexión local con Resolve, subtítulos dinámicos multicapa, marcadores en línea de tiempo, escritura en la pista nativa, efectos Fusion editables, locución y autocorrección con IA, proveedores de IA intercambiables, servidor MCP propio por stdio, auto-actualización desde GitHub Releases, instalador Inno Setup y diálogo «Acerca de»

## Selección

La regla de selección y el orden de autoridad están en [gobernanza documental](../../../Docs/global/documentation/documentation-governance.md) y en [reglas de trabajo del agente](../../../Docs/global/documentation/agent-working-rules.md): se consultan solo los módulos globales, el tipo, las plataformas, el stack y las funciones realmente adoptadas. Una capacidad opcional no se aplica por semejanza de stack.

## Módulos Core que aplican a este proyecto

| Ámbito | Módulo |
|---|---|
| Global | [calidad](../../../Docs/global/quality/quality-baseline.md), [procesos](../../../Docs/global/documentation/process-workflow.md), [gobernanza](../../../Docs/global/documentation/documentation-governance.md), [arquitectura](../../../Docs/global/architecture/architecture-baseline.md), [carpetas](../../../Docs/global/architecture/project-structure.md), [scripts](../../../Docs/global/architecture/command-scripts-standard.md), [Mise](../../../Docs/global/architecture/mise-command-standard.md), [diseño](../../../Docs/global/design/design_system.md), [textos de interfaz](../../../Docs/global/design/interface-writing.md), [seguridad](../../../Docs/global/security/security-baseline.md) |
| Releases | [base](../../../Docs/global/releases/release-baseline.md), [protocolo](../../../Docs/global/releases/protocolo_lanzamiento_actualizacion.md), [release message web](../../../Docs/global/releases/web-release-message-standard.md) |
| Plataforma | [instalación en Windows](../../../Docs/platforms/windows/installer.md) |
| Stack | [Python](../../../Docs/stacks/python/python-baseline.md) |
| Funciones | [instalador](../../../Docs/features/installer/README.md), [auto-actualización](../../../Docs/features/auto-updater/auto_updater.md), [modelos de IA](../../../Docs/features/ai-models/README.md), [soporte oficial](../../../Docs/features/official-support/official-support-baseline.md) |
| Diagnóstico | [problemas conocidos](../../../Docs/troubleshooting/README.md) |

## Excepciones locales

- El tipo `desktop` de Core describe aplicaciones nativas Rust/Tauri; este proyecto es Python/Flet y aplica su propia base de stack. Las reglas de esa carpeta que no dependan del runtime (instalador, «Acerca de», actualización, releases) sí se aplican.
- La bandeja del sistema todavía no es una función activa.
- La compatibilidad con macOS se conserva como objetivo futuro, pero no se declara validada.
- La sincronización de la ficha del producto en Aurora no está automatizada en el repositorio; se realiza por el canal administrativo del estándar de release message web.
