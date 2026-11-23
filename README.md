# DaVinci Flow

La rama `main` contiene DaVinci Flow en Rust + GPUI. `mise dev` abre la edición de tu rama desde tu carpeta actual. [Guía de GPUI](docs/GPUI.md) · [Edición Flet 1.0.0 descontinuada](https://github.com/biglexj/DaVinciFlow/tree/v-python).

DaVinci Flow es una aplicación para automatizar la edición en DaVinci Resolve 21. Su flujo editorial va de la transcripción a la propuesta, la revisión y la aplicación de títulos Text+ editables. Luna Fetch incorpora medios al Media Pool.

El [catálogo visual y los presets](docs/es/guides/catalogo-y-presets-textplus.md) permiten consultar títulos instalados, reproducir sus muestras originales disponibles y guardar selecciones reutilizables. La escritura editorial utiliza bases DRB o del Media Pool; los SETTING/DRFX sin base nativa se detienen antes de escribir. La validación real de la nueva colección editorial sigue pendiente.



## Organización de recursos

El icono canónico de identidad se conserva en [`assets/branding/icons/icon-transparent.png`](assets/branding/icons/icon-transparent.png). Los recursos derivados deben generarse desde esa fuente conforme al [Asset Organization Standard](../Docs/global/architecture/asset-organization-standard.md); las capturas documentales viven en `docs/screenshots/`.

---

## 🚀 Capacidades Principales

- **Transcripción como fuente de verdad**: Lee la pista nativa o un SRT; las capas son un resultado del análisis, no la entrada.
- **Clasificación semántica determinista**: Desglose en hasta 3 capas de texto (`DF_CONTEXT`, `DF_MAIN`, `DF_ACCENT`) e intención comunicativa (`statement`, `question`, `exclamation`, `emphasis`, `negation`).
- **Brand Guard y temas oficiales**: Soporte estricto para los temas **Ely** y **Aurora** con validación de paletas HEX y fuentes tipográficas oficiales.
- **Títulos editoriales nativos**: Copia bases DRB/Media Pool y verifica pista, inicio, duración y texto, conservando su diseño. La validación completa de la nueva colección en Resolve sigue pendiente.
- **Proveedores de IA intercambiables**: Capa `ai/providers` con adaptadores de **Google Gemini** y **Minimax** tras un contrato común; el proveedor se elige en Ajustes.
- **Generación de voz**: Voces locales de Windows y generación remota con Aurora a través del adaptador de compatibilidad.
- **Autocorrector auditable**: Normalización, glosario e IA por etapas separadas, con el diff de cada subtítulo.
- **Efectos Fusion editables**: Composiciones y títulos nativos (`Text+`, `Fade On`, `Headline`) que se siguen editando en el Inspector, nunca renderizados.
- **Subtítulos en la pista nativa**: Escritura de cues en la pista `subtitle` de Resolve, con verificación posterior.
- **DaVinci Flow como herramienta MCP**: Las mismas operaciones publicadas como herramientas MCP para que cualquier agente pueda operarlo ([guía](docs/MCP_SERVIDOR.md)).
- **Motor SFX funcional**: Propone y materializa WAV originales de DaVinci Flow, con control de densidad y soporte para `[SFX_OFF]`.
- **Idempotencia**: Un mismo plan reutiliza sus clips identificados en vez de duplicarlos.
- **Reversión selectiva**: El botón Deshacer retira únicamente la última ejecución registrada; no vacía todas las pistas DF.

---

## Arquitectura

- `src/` contiene el motor Rust. Las vistas y acciones de GPUI se organizan por función en `src/app/`.
- `src/resolve_scripts/` contiene las operaciones que se ejecutan dentro del MCP de Resolve.
- `compat/python/` contiene el puente y sus pruebas para los flujos pendientes de migración.
- `assets/` contiene los recursos de producto. Los artefactos de Cargo se generan en `target/`.

El [mapa del proyecto](docs/arquitectura.md) y la [guía de GPUI](docs/GPUI.md) describen los módulos y los límites de la migración.

## Ejecutar

Requisitos de desarrollo: Windows, Rust y Mise. La integración con la línea de tiempo requiere el MCP oficial de DaVinci Resolve Studio. Luna Fetch utiliza `yt-dlp` y FFmpeg en `PATH`.

```powershell
mise dev
mise dev "ruta/al/archivo.srt"
```

| Tarea | Propósito |
|---|---|
| `mise setup` | Preparar los adaptadores de Resolve y Aurora en `.venv`. |
| `mise build` | Compilar el ejecutable Rust. |
| `mise check` | Comprobar formato y Clippy. |
| `mise test` | Ejecutar las pruebas de Rust. |

Las tareas admiten `--plan` para ver el comando. El instalador nativo está pendiente.

## 🔌 DaVinci Flow como herramienta MCP

Además de la interfaz, DaVinci Flow publica sus operaciones como un **servidor MCP por stdio**. Así cualquier agente puede capturar subtítulos, generar una propuesta, aplicarla revisada, insertar títulos nativos, crear efectos Fusion editables, generar voz, autocorregir y escribir en la pista nativa sin depender de la ventana abierta.

```powershell
.venv/Scripts/python.exe -m davinci_flow.mcp_server
```

La propuesta sigue exigiendo revisión explícita (`reviewed: true`) antes de aplicarse, y una escritura que Resolve no confirma no se reintenta a ciegas. Consulta la [guía del servidor MCP](docs/MCP_SERVIDOR.md) para el registro en un cliente y el catálogo completo de herramientas.

---

## 📖 Guía de Uso por Terminal

Después de `mise setup`, la CLI de compatibilidad se ejecuta desde el mismo checkout.

### 1. Información y Acerca de
```powershell
.venv/Scripts/python.exe -m davinci_flow --about
```

### 2. Previsualizar el Plan de Capas (Modo Seco)
```powershell
.venv/Scripts/python.exe -m davinci_flow --plan --track 1 --theme ely --profile natural
```

### 3. Exportar el Plan Calculado a Archivo JSON
```powershell
.venv/Scripts/python.exe -m davinci_flow --plan --export-plan "temp/plan_generacion.json"
```

### 4. Simulación de Generación (Dry-Run)
```powershell
.venv/Scripts/python.exe -m davinci_flow --generate --dry-run --theme ely
```

También puedes previsualizar un plan directamente desde un archivo SRT **sin necesidad de tener DaVinci Resolve abierto**:
```powershell
.venv/Scripts/python.exe -m davinci_flow --generate --dry-run --srt "temp/demo.srt" --theme ely
```

### 5. Comparar y Reconciliar contra un Plan Previo
```powershell
.venv/Scripts/python.exe -m davinci_flow --reconcile "temp/plan_generacion.json"
```

### 6. Experimento: Gemini Decision 1 frente al motor actual
```powershell
.venv/Scripts/python.exe -m davinci_flow --experiment decision1 --srt "temp/demo.srt" --compare --experiment-out "temp/experimento.json"
```

Compara el motor de decisiones `gemini-decision-1` con el motor editorial
actual sobre el mismo SRT: latencia, consumo, acuerdo por bloque y
cumplimiento del contrato. Guarda el informe y una **propuesta sin revisar**
que se abre en el Editor para revisarla a mano. No escribe en Resolve.

---

## 🧪 Ejecución de Pruebas Automatizadas

```powershell
mise test
```

Pruebas del puente, después de `mise setup`:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

La validación del 21 de agosto de 2026 leyó 369 subtítulos reales de `Timeline 1` y comprobó una muestra reversible de tres capas Fusion más un SFX. Esta evidencia no sustituye la revisión visual y auditiva de Biglex antes de generar toda la línea de tiempo.

---

## 👤 Autor y Licencia

- **Autor**: biglexj (2026)
- **Licencia**: MIT
- **Donaciones Oficiales**: [https://www.biglexj.com/donaciones](https://www.biglexj.com/donaciones)
- **Buy Me a Coffee**: [https://buymeacoffee.com/biglexj](https://buymeacoffee.com/biglexj)
- **GitHub**: [https://github.com/biglexj](https://github.com/biglexj)
