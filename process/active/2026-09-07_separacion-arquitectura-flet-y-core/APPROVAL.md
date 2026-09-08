# Aprobación: Separación de arquitectura Flet y Core

## Decisión de Aprobación

- **Fecha**: 2026-09-07
- **Aprobado por**: biglexj (autorización verbal directa por audio el 2026-09-07 21:52)
- **Estado**: En proceso de ejecución técnica
- **Notas**: Autorizada la separación limpia en `src/davinci_flow` (backend/core) y `src-flet` (frontend/diseño), consolidación en CPython 3.13 con `uv`, purga de `.venv-pypy` y `.venv-resolve`, y posterior documentación en la base Core Docs.
