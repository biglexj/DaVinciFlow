---
trigger: always_on
---

# Perfil de Documentación Core — DaVinci Flow

- Última revisión: 2026-08-17
- Tipo principal: `Automatización para aplicación de escritorio`
- Plataformas: `Windows 11 y DaVinci Resolve 21`
- Stack: `Python 3.11 de 64 bits, API de scripting de DaVinci Resolve y unittest`
- Funciones activas: `Conexión local con Resolve, generación de subtítulos dinámicos multicapa, marcadores en línea de tiempo e integración opcional con Gemini para alineación de guion`

## Regla de selección

Antes de aplicar la Documentación Core, completar este perfil con el alcance real del proyecto y consultar únicamente:

1. Las reglas globales pertinentes.
2. El tipo principal en `Core-Docs/types`.
3. Cada plataforma distribuida en `Core-Docs/platforms`.
4. El stack utilizado en `Core-Docs/stacks`.
5. Las funciones realmente adoptadas en `Core-Docs/features`.

No aplicar una capacidad por semejanza. Instancia única, bandeja, autoactualización, instalador, IA y otras funciones deben figurar expresamente como activas.

## Documentos Core seleccionados

- `global/architecture/architecture-baseline.md`
- `global/documentation/process-workflow.md`
- `global/documentation/documentation-governance.md`
- `global/quality/quality-baseline.md`
- `global/security/security-baseline.md`
- `features/ai-models/README.md`
- `types/multiplatform/README.md`, únicamente para encapsular dependencias de plataforma.

## Excepciones locales

- La autoactualización y la bandeja del sistema todavía no son funciones activas.
- La compatibilidad con macOS se conserva como objetivo futuro, pero no se declara validada.
