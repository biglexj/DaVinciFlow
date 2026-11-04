---
trigger: always_on
---

# Mapa de carpetas — DaVinci Flow

> Mapa de implementación local. Describe dónde vive hoy el código, no una norma global. Las reglas compartidas de estructura están en [organización de proyectos](../../../Docs/global/architecture/project-structure.md) y en la [base de Python](../../../Docs/stacks/python/python-baseline.md); este archivo solo fija las rutas y convenciones reales del proyecto.

## Raíz del repositorio

```text
DaVinciFlow/
├── .agents/rules/          # Reglas locales del agente (base.md, core_profile.md, folder_structure.md)
├── src/davinci_flow/       # Motor headless: dominio, Resolve, IA, subtítulos, SFX, voz
│   ├── ai/                 # Proveedores de IA y credenciales
│   ├── editorial/          # Propuesta editorial, puente con Resolve y escritura
│   ├── generation/         # Planes, plantillas Fusion, portadoras y registros
│   ├── resolve/            # Adaptadores exclusivos de la API de DaVinci Resolve
│   ├── sfx/                # Catálogo y motor de efectos de sonido
│   ├── subtitles/          # Modelo de subtítulos, normalizador, clasificador, autocorrector
│   ├── themes/             # Tokens oficiales Ely/Aurora y Brand Guard
│   ├── updater/            # Comprobación de actualizaciones y sanitización de notas
│   └── voice/              # Locución sintética
├── src-flet/               # Interfaz de escritorio Flet
│   ├── app/                # Shell de la ventana y ciclo de vida
│   ├── features/           # Vistas por dominio (editor, catalog, library, settings)
│   └── shared/             # Componentes y utilidades visuales transversales
├── assets/                 # Recursos maestros de marca (iconos, plantillas)
├── packaging/windows/      # Empaquetado Inno Setup (setup.iss, identity.iss, version.iss, launcher/)
├── scripts/                # Implementación de las tareas: mise-task.ts, release/, packaging/, arranque
├── docs/                   # Documentación funcional y contratos propios del proyecto
│   └── es/guides/          # Guías de uso en español
├── process/                # Procesos: active/, completed/, archive/
├── tests/                  # Pruebas permanentes (unittest)
├── release/                # Artefactos de distribución generados (instalador y SHA256SUMS.txt)
├── dist/                   # Paquetes Python generados por la build
├── temp/                   # Borradores (ignorado por git)
├── scratch/                # Utilidades de mantenimiento (ignorado por git)
├── test/                   # Pruebas temporales (ignorado por git)
├── mise.toml               # Tareas canónicas del proyecto
├── pyproject.toml          # Fuente de verdad de la versión y de las dependencias
├── ROADMAP.md              # Pendientes generales e historial del producto
├── RELEASE_NOTES.md        # Historial de cambios por versión
├── RELEASE_MESSAGE.md      # Mensaje público del último lanzamiento
├── AI_MODELS.md            # Registro local de modelos de IA
└── README.md               # Documentación pública del proyecto
```

## Convenciones de nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Módulos y paquetes Python | `snake_case` | `fusion_effects.py`, `src/davinci_flow/ai/providers/` |
| Clases, dataclasses y modelos | `PascalCase` | `EditorialOptions`, `SubtitleCue` |
| Constantes de módulo | `SCREAMING_SNAKE_CASE` | `PROTOCOL_VERSION`, `DEFAULT_MODEL` |
| Funciones y variables | `snake_case` | `propose()`, `build_text_provider()` |
| Vistas de Flet | `snake_case` por dominio | `src-flet/features/editor/editor_view.py` |
| Carpetas de dominio en la interfaz | `snake_case` en minúscula | `features/catalog/`, `features/settings/` |

## Reglas estructurales locales

- Permitido: añadir módulos dentro del dominio al que pertenecen; crear componentes en `shared/` solo si los usan dos o más vistas; usar `temp/`, `scratch/` y `test/` en la raíz.
- Prohibido: crear `scratch/` o `test/` dentro de `src/`, `src-flet/` o cualquier carpeta de código; dejar lógica de negocio suelta en la raíz de `src/`; duplicar un componente ya presente en `shared/`; crear carpetas genéricas (`utils/`, `helpers/`, `misc/`) en la raíz.
- El motor (`src/davinci_flow/`) no importa Flet; la interfaz (`src-flet/`) no habla directamente con la API de Resolve.
- Los recursos derivados (capturas, iconos derivados, artefactos de compilación) no se versionan en su carpeta de origen: se generan desde el maestro o desde el empaquetado.
- El límite de tamaño de archivo y su excepción se aplican según la [base de Python](../../../Docs/stacks/python/python-baseline.md) y la decisión local registrada en [base.md](base.md).
