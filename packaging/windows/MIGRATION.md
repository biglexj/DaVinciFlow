# Migración y coexistencia — instalador de Windows de DaVinci Flow

Documento de referencia del instalador `DaVinciFlow-Setup-<version>.exe`
(plantilla compartida **Biglex Modern 2.0**, Inno Setup 6.7.3).

Fecha de la revisión: 21 de octubre de 2026.

---

## 1. Qué se distribuyó hasta ahora

DaVinci Flow **no tenía instalador de Windows**. El estado real del proyecto
antes de este trabajo era:

| Elemento | Estado real |
| --- | --- |
| Aplicación de escritorio | Es una app **Flet** (Python) en `src-flet\`, ejecutada en modo desarrollo: `.venv\Scripts\python.exe src-flet\main.py` (ver `scripts\start-desktop.ps1`). |
| Ejecutable de escritorio | **No existía ningún `.exe`.** Búsqueda en el repo: 0 archivos `.exe`, `.bat` o `.cmd` propios (fuera de `.venv`). |
| Distribución publicada | `scripts\release\build-release.ps1` genera una **rueda y un sdist** (`uv build` → `dist\*.whl`, `dist\*.tar.gz`) y los publica en GitHub Releases. `pyproject.toml` solo empaqueta `src/` (`davinci_flow`), **no** `src-flet/`. |
| Preparación del entorno | `scripts\setup-desktop.ps1` (`uv sync` + registro del lanzador en el menú de Resolve). |
| Integración con Resolve | `src\davinci_flow\installer.py` escribe un script Python en el menú *Scripts* de DaVinci Resolve (`%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\DaVinci Flow.py`) que apunta al **directorio fuente del checkout**. |
| Datos del usuario | `%USERPROFILE%\.davinci_flow\` (configuración, preferencias, registros, logs, plantillas generadas, runtime). Vive fuera de la carpeta de instalación. |

Conclusión: la app de escritorio **solo se ejecutaba en modo desarrollo**. Este
trabajo añade el primer artefacto de escritorio distribuible y su instalador.

## 2. Qué empaqueta el instalador ahora

El instalador instala un **bundle onedir de PyInstaller** (`DaVinciFlow.exe` +
`_internal\`), construido por `packaging\windows\launcher\DaVinciFlow.spec`:

- `src-flet\` (interfaz Flet) y `src\` (núcleo `davinci_flow`) empaquetados como
  módulos.
- El **cliente de escritorio de Flet** (`flet-windows.zip`, v0.86.5) incluido en
  `_internal\flet_desktop\app\`: la primera ejecución **no descarga nada** de
  internet.
- Los recursos de marca (`assets\branding\icons\`) dentro del bundle, para que
  el icono de la ventana sea el oficial.

Motivo de la decisión: la alternativa sería instalar el código fuente y pedir
`uv sync` al usuario, lo que no es un instalador y deja al usuario sin Python
ni con `uv`. El bundle onedir es autocontenido, arranca sin consola y no
depende de la red tras la instalación.

**Restricción del bundle:** el cliente de Flet se extrae en la primera
ejecución a `%USERPROFILE%\.flet\client\flet-desktop-full-0.86.5\` (comportamiento
propio de Flet). Esa carpeta es una caché de la app, no un dato del usuario, y
el desinstalador no la toca.

## 3. Identidad de actualización

| Clave | Valor |
| --- | --- |
| `AppId` | `{4E7B2A63-1C05-4F3D-9A28-6D5B0C91F4E2}` |
| `AppName` | DaVinci Flow |
| Carpeta | `{localappdata}\Programs\DaVinciFlow` |
| Ejecutable | `{app}\DaVinciFlow.exe` |
| Privilegios | `lowest` (por usuario, sin elevación) |
| Clave de registro | `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{4E7B2A63-…}_is1` |

El `AppId` es **nuevo y propio** de DaVinci Flow: no reutiliza el de la
plantilla (`Biglex.InnoModern.TemplatePreview`) ni el de ninguna otra app de
Biglex. Como no existía un instalador previo, no hay una identidad que
migrar y **no se puede reutilizar un `UpgradeCode` de MSI** porque DaVinci Flow
nunca se distribuyó por MSI.

Forma de escritura en `setup.iss`: `AppId={{#MyAppId}` (doble llave **solo en
la apertura**). Con `{#MyAppId}` a secas, Inno Setup interpreta el GUID entre
llaves como una constante de la sección `[Setup]` y la compilación falla con
*Unknown constant*.

## 4. Coexistencia con lo que hay hoy

- **Rueda y sdist de Python:** conviven sin conflicto. El instalador **no**
  instala la rueda ni modifica el `.venv` del repositorio. Quien use el flujo
  `uv sync` + `scripts\start-desktop.ps1` sigue trabajando igual, sobre el
  código fuente.
- **Lanzador del menú de Resolve:** `src\davinci_flow\installer.py` sigue
  apuntando al **checkout de código fuente**, no a la app instalada. Ambos
  caminos son válidos: el menú de Resolve abre la versión de desarrollo y el
  instalador abre la versión empaquetada. Si se quisiera que el menú de Resolve
  abriera la app instalada habría que cambiar `installer.py`, que es código de
  producción y queda fuera de este trabajo.
- **Instalaciones previas:** este instalador es la primera instalación de
  DaVinci Flow en Windows. Si existiera otra instalación hecha a mano (una
  carpeta copiada, por ejemplo), **no se borra**: el instalador solo escribe en
  `{app}` y en su propia clave de registro.
- **Datos del usuario:** `%USERPROFILE%\.davinci_flow\` no se toca ni al
  instalar ni al desinstalar. Verificado: tras desinstalar, `config.json`,
  `editorial_preferences.json`, `records\`, `generated\` y `logs\` siguen
  intactos.
- **Accesos directos:** el instalador crea el acceso directo en el menú de
  inicio y en el escritorio. Ambos los retira el desinstalador.

## 5. winget

**No existen manifiestos winget para DaVinci Flow** (a diferencia de
`Ely-Tesia`, `Gallery-DL-GUI`, `Luna---Fetch` y `WinTTS`, que sí tienen
`packaging\winget\` en este ecosistema). No se publica nada.

Si se quisiera preparar el manifiesto más adelante, el cambio de tipo sería:

- `PackageType: exe`
- `InstallerType: inno`
- `InstallerSwitches`: `Silent: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
  y `SilentWithProgress: /SILENT /SUPPRESSMSGBOXES /NORESTART`
- `UpgradeBehavior: install`
- `ProductCode`: el propio `AppId` del instalador
- `Commands`: sin `Modify` (este instalador no tiene modo de cambio).

Esto queda **preparado, no publicado**, y sin tocar ningún manifiesto.

## 6. Reinstalación y actualización

El `AppId` es estable, así que una versión nueva **actualiza la anterior en el
mismo sitio**: no crea una instalación paralela. La carpeta de instalación
mantiene la ruta por usuario y el registro conserva una sola clave
`{4E7B2A63-…}_is1`.

La carpeta `_internal\` se **reescribe** en cada instalación: los `[Files]` del
script no usan `ignoreversion` porque los binarios internos no llevan
información de versión y quedarían obsoletos sin replaced.

## 7. Qué se hace y qué no

| Área | Alcance |
| --- | --- |
| Presentación del instalador | Plantilla Biglex Modern 2.0 (entrada → progreso → éxito, sin páginas extra). |
| Artefacto de escritorio | Nuevo: bundle PyInstaller + script de build propios. |
| Código de producción (`src\`, `src-flet\`) | **Sin cambios.** |
| `pyproject.toml`, `.gitignore` | **Sin cambios.** |
| Manifiestos winget | **No hay** y no se publica nada. |

## 8. Compilar

```powershell
pwsh -File scripts\packaging\Build-Installer.ps1
```

El script:

1. Lee la versión real de `pyproject.toml` y regenera
   `packaging\windows\version.iss`.
2. Prepara el entorno de compilación (`uv venv` + `flet[desktop]==0.86.5` +
   `pyinstaller`), descarga el cliente de Flet si no está en caché y compila el
   bundle de escritorio.
3. Compila `packaging\windows\setup.iss` con
   `D:\Proyectos\biglexj\Scripts\tools\InnoSetup\ISCC.exe` y deja el instalador
   en `dist\`.
4. Comprueba con `git check-ignore` que los archivos de empaquetado siguen
   versionados.

Salida: `dist\DaVinciFlow-Setup-0.3.0.exe`.

## 9. Notas de validación

Ver `packaging\windows\VALIDATION.md` para el detalle de lo comprobado
físicamente en esta máquina (teclado, capturas por tema, instalación,
desinstalación, reinstalación) y de lo que queda pendiente (escalas de DPI del
sistema y nombres largos de aplicación, que requieren reiniciar sesión).
