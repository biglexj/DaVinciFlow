---
trigger: always_on
---

# Reglas locales — DaVinci Flow

## Identidad y alcance

- Proyecto: DaVinci Flow.
- Autor: biglexj.
- Licencia: MIT.
- Producto actual: automatización para DaVinci Resolve 21, no aplicación independiente.
- Stack activo: Python 3.13 de 64 bits y API de scripting de DaVinci Resolve 21.
- Las plantillas visuales futuras usarán Fusion `.setting` y exclusivamente temas oficiales de Aurora o Ely.

## Arquitectura

- Separar dominio, aplicación e infraestructura mediante responsabilidades reconocibles.
- Encapsular la API de Resolve detrás de adaptadores comprobables con objetos simulados.
- Mantener la lógica reutilizable fuera de las entradas de consola o interfaz.
- No crear módulos para funciones todavía inactivas.
- Evitar archivos de más de 900 líneas; 1200 líneas es el máximo excepcional.
- Usar `temp/` para borradores, `scratch/` para mantenimiento y `test/` para pruebas temporales. Las pruebas permanentes viven en `tests/`.

## Flujo de trabajo

- Cada trabajo planificado vive en `process/active/YYYY-MM-DD_objetivo/` con `PLAN.md`, `TASKS.md`, `VALIDATION.md` y `APPROVAL.md`.
- `ROADMAP.md` conserva el trabajo general; no crear `TASKS.md` en la raíz.
- Registrar evidencia real en `VALIDATION.md`. Una prueba unitaria no sustituye la verificación dentro de Resolve.
- No anunciar una versión como publicada sin comprobar el remoto cuando el usuario solicite un lanzamiento.
- Mantener las reglas de `.agents/rules/` por debajo de 12 000 caracteres.

## IA y secretos

- La integración con modelos de lenguaje es opcional y permanece inactiva hasta que exista un caso de uso aprobado.
- Usar adaptadores independientes del proveedor; no fijar catálogos de modelos actuales en reglas globales.
- Mantener claves fuera del repositorio, los registros y la interfaz visible.
- Crear `AI_MODELS.md` solo cuando la función de IA se active, siguiendo `Core-Docs/features/ai-models`.

## Fuentes compartidas

- Documentación base: `D:\Proyectos\biglexj\Core-Docs`.
- Perfil aplicable: `.agents/rules/core_profile.md`.
- Instrucciones detalladas: `agent.md`.
- Aurora es una referencia selectiva; sus configuraciones particulares no se copian automáticamente.
