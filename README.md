# DaVinci Flow

DaVinci Flow es una automatización modular en Python para DaVinci Resolve 21. Primero analiza la transcripción existente —pista de subtítulos nativa o archivo SRT— y, a partir de ese texto y sus tiempos, decide la jerarquía de capas, los títulos Fusion y las propuestas de efectos sonoros.

## 📸 Capturas de Pantalla

![Editor de subtítulos](docs/screenshots/editor.png)

## Organización de recursos

El icono canónico de identidad se conserva en [`assets/branding/icons/icon-transparent.png`](assets/branding/icons/icon-transparent.png). Los recursos derivados deben generarse desde esa fuente conforme al [Asset Organization Standard](../Docs/global/architecture/asset-organization-standard.md); las capturas documentales viven en `docs/screenshots/`.

---

## 🚀 Capacidades Principales

- **Transcripción como fuente de verdad**: Lee la pista nativa o un SRT; las capas son un resultado del análisis, no la entrada.
- **Clasificación semántica determinista**: Desglose en hasta 3 capas de texto (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) e intención comunicativa (`statement`, `question`, `exclamation`, `emphasis`, `negation`).
- **Brand Guard y temas oficiales**: Soporte estricto para los temas **Ely** y **Aurora** con validación de paletas HEX y fuentes tipográficas oficiales.
- **Composiciones Fusion propias**: Cada capa se inserta con pista, inicio y duración verificados contra el `TimelineItem` devuelto por Resolve.
- **Motor SFX funcional**: Propone y materializa WAV originales de DaVinci Flow, con control de densidad y soporte para `[SFX_OFF]`.
- **Idempotencia**: Un mismo plan reutiliza sus clips identificados en vez de duplicarlos.
- **Reversión selectiva**: El botón Deshacer retira únicamente la última ejecución registrada; no vacía todas las pistas DF.

---

## 🏛️ Arquitectura Modular

```text
src/davinci_flow/
├── __main__.py              Entrada CLI principal (planificación, generación, auditoría)
├── application.py           Coordinación de casos de uso del producto
├── errors.py                Jerarquía de errores controlados
├── generation/              Plan de generación, diffs, plantillas Fusion y registros
│   ├── fusion_template.py   Generador de composiciones Fusion y conversión de color
│   ├── carrier_media.py     AVI mínimo para duración exacta de composiciones Fusion
│   ├── plan.py              Modelo GenerationPlan versionado (1.0.0) y persistencia
│   ├── reconciler.py        Motor de reconciliación y diff de subtítulos
│   └── record.py            Auditoría de clips generados y reversión
├── resolve/                 Adaptadores exclusivos para DaVinci Resolve API
│   ├── client.py            Conexión segura y detección de sesión
│   ├── subtitle_reader.py   Lector y normalizador de pistas
│   ├── timeline_writer.py   Inserción y reversión en pistas dedicadas
│   └── track_manager.py     Gestión de pistas DF_CONTEXT, DF_MAIN, DF_ACCENT, DF_SFX
├── sfx/                     Biblioteca y motor de efectos de sonido
│   ├── catalog.py           Descriptor auditable AssetDescriptor y catálogo
│   ├── assets.py            Materialización de WAV procedurales incluidos
│   └── engine.py            Motor de propuesta y perfiles de densidad
├── subtitles/               Modelos de dominio, normalizador y clasificador
│   ├── block.py             CaptionBlock con roles y trazabilidad
│   ├── classifier.py        Clasificador de capas semánticas en español
│   ├── fingerprint.py       Huellas SHA-256 e identificadores estables
│   ├── model.py             SubtitleCue nativo
│   └── normalizer.py        Normalizador ortográfico y de caracteres especiales
└── themes/                  Tokens oficiales y Brand Guard
    └── tokens.py            ThemeTokens, temas Ely/Aurora y validación estricta
```

---

## 🛠️ Requisitos del Entorno

- **Sistema Operativo**: Windows 11 (64 bits).
- **Entorno Host**: DaVinci Resolve 21 (Studio o Free con scripting habilitado).
- **Interfaz de escritorio**: Flet 0.86.5 sobre PyPy 7.3.23 (Python 3.11.15), gestionado con uv.
- **Puente de Resolve**: CPython 3.13 de 64 bits, en un entorno independiente. En esta instalación, `fusionscript.dll` de Resolve 21 no es compatible con Python 3.11/3.12.
- **Dependencias**: el extra `desktop` instala Flet y su cliente Flutter; el puente usa la biblioteca estándar y la API de Resolve.

### Preparar y abrir la interfaz

```powershell
./scripts/setup-desktop.ps1
./scripts/start-desktop.ps1
```

La preparación crea `.venv-pypy` y `.venv-resolve` mediante `uv sync --locked`, y actualiza el acceso **Área de trabajo → Secuencias de comandos → DaVinci Flow**. El entorno `.venv` anterior se conserva. El menú de Resolve, `--ui` y `--editorial-ui` abren la misma ventana Flet; una segunda apertura trae la primera al frente. El auxiliar de CPython se inicia únicamente para capturar, leer plantillas del proyecto, aplicar o deshacer.

El editor, las plantillas, la biblioteca por categorías y los ajustes comparten ventana. La propuesta sigue requiriendo revisión antes de aplicar. PyPy no carga `fusionscript.dll`: intercambia datos JSON con el auxiliar por sus tuberías de proceso. No hay un servidor RPC abierto ni reintentos automáticos de escrituras.

La compatibilidad Flet/PyPy usa un selector de archivos y carpetas hecho con controles Flet, centrado y sin servicios basados en conteo de referencias. El cliente Flutter se espera mediante un hilo para evitar un error de cierre de `asyncio.subprocess` en PyPy para Windows. No se han modificado instalaciones de Flet ni de PyPy. Esta integración no demuestra por sí sola una mejora de FPS o menor consumo de RAM.

La biblioteca comparte únicamente nombres de los recursos elegidos con la IA. La inserción editorial de visuals, música y las dos capas de SFX sigue en las fases siguientes. Consulta la [validación de la migración](process/active/2026-09-07_interfaz-flet/VALIDATION.md).

---

## 📖 Guía de Uso por Terminal

Configurar la ruta del paquete:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

### 1. Información y Acerca de
```powershell
uv run --python 3.13 python -m davinci_flow --about
```

### 2. Previsualizar el Plan de Capas (Modo Seco)
```powershell
uv run --python 3.13 python -m davinci_flow --plan --track 1 --theme ely --profile natural
```

### 3. Exportar el Plan Calculado a Archivo JSON
```powershell
uv run --python 3.13 python -m davinci_flow --plan --export-plan "temp/plan_generacion.json"
```

### 4. Simulación de Generación (Dry-Run)
```powershell
uv run --python 3.13 python -m davinci_flow --generate --dry-run --theme ely
```

También puedes previsualizar un plan directamente desde un archivo SRT **sin necesidad de tener DaVinci Resolve abierto**:
```powershell
uv run --python 3.13 python -m davinci_flow --generate --dry-run --srt "temp/demo.srt" --theme ely
```

### 5. Comparar y Reconciliar contra un Plan Previo
```powershell
uv run --python 3.13 python -m davinci_flow --reconcile "temp/plan_generacion.json"
```

---

## 🧪 Ejecución de Pruebas Automatizadas

```powershell
$env:PYTHONPATH = "$PWD\src"
uv run --python 3.13 python -m unittest discover -s tests -v
```

La validación del 21 de agosto de 2026 leyó 369 subtítulos reales de `Timeline 1` y comprobó una muestra reversible de tres capas Fusion más un SFX. Esta evidencia no sustituye la revisión visual y auditiva de Biglex antes de generar toda la línea de tiempo.

---

## 👤 Autor y Licencia

- **Autor**: biglexj (2026)
- **Licencia**: MIT
- **Donaciones Oficiales**: [https://www.biglexj.com/donaciones](https://www.biglexj.com/donaciones)
- **Buy Me a Coffee**: [https://buymeacoffee.com/biglexj](https://buymeacoffee.com/biglexj)
- **GitHub**: [https://github.com/biglexj](https://github.com/biglexj)
