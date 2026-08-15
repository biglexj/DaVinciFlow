---
trigger: always_on
---

# Perfil de Documentación Core — DaVinci Flow

- Última revisión: 2026-08-15
- Tipo principal: `Automatización para aplicación de escritorio`
- Plataformas: `Windows 11 y DaVinci Resolve 21`
- Stack: `Python 3.11 de 64 bits, API de scripting de DaVinci Resolve y unittest`
- Funciones activas: `Conexión local con Resolve y lectura no destructiva de subtítulos`

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
- `types/multiplatform/README.md`, únicamente para encapsular dependencias de plataforma.

## Excepciones locales

- La interfaz, el instalador, la autoactualización y la integración con IA todavía no son funciones activas.
- La compatibilidad con macOS se conserva como objetivo futuro, pero no se declara validada.

