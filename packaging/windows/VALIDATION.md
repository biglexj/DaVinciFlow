# Validación — instalador de Windows de DaVinci Flow (Biglex Modern 2.0)

Revisión del 21 de octubre de 2026, en la máquina de trabajo del ecosistema
Biglex (`D:\Proyectos\biglexj`). Todas las capturas están en
`packaging\windows\validation\`.

> Nada de esta tabla es una aceptación visual humana: son comprobaciones
> técnicas ejecutadas sobre el instalador compilado y ejecutado en esta
> máquina.

## 1. Entorno

| Dato | Valor |
| --- | --- |
| Compilador | Inno Setup 6.7.3 (`D:\Proyectos\biglexj\Scripts\tools\InnoSetup\ISCC.exe`) |
| Plantilla | Biglex Modern 2.0 (`BiglexModernUI.iss` del 21-10-2026, con `ModernAppName`) |
| Versión instalada | 0.3.0 (leída de `pyproject.toml`) |
| Tema de Windows | `AppsUseLightTheme=0` → Windows en **oscuro** |
| Escala del sistema | `AppliedDPI=96` → **100 %** |
| Python del bundle | CPython 3.13.14 (venv propio de compilación, `uv venv`) |
| PyInstaller | 6.22.3 |
| Flet | 0.86.5 (cliente de escritorio incluido en el bundle) |
| Privilegios | Instalación por usuario, sin elevación (`PrivilegesRequired=lowest`) |

## 2. Compilación

Comandos ejecutados:

```powershell
& 'D:\Proyectos\biglexj\DaVinciFlow\scripts\packaging\Build-Installer.ps1'
```

Salida real (última ejecución completa):

```
==> Leyendo la version de pyproject.toml
    version: 0.3.0
    escrito: D:\Proyectos\biglexj\DaVinciFlow\packaging\windows\version.iss
==> Preparando el entorno de compilacion del ejecutable de escritorio
    instalando flet[desktop] y pyinstaller...
==> Preparando el cliente de escritorio de Flet
    en cache: D:\...\packaging\windows\build\cache\flet-windows.zip
==> Compilando el ejecutable de escritorio (PyInstaller, onedir)
==> Sincronizando el icono oficial con la carpeta de empaquetado
==> Compilando el instalador con Inno Setup

Instalador generado:
    D:\Proyectos\biglexj\DaVinciFlow\dist\DaVinciFlow-Setup-0.3.0.exe
    sha256: 2596c3c44ad334c114551b5d5da4fdf4d47240c5e32be1fb99d2c8cf9d971505
    tamano: 54.5 MB
==> Comprobando que el empaquetado sigue versionado en git
    todos los archivos de empaquetado estan versionados.
```

Salida del compilador de Inno:

```
Successful compile (17.172 sec). Resulting Setup program filename is:
D:\Proyectos\biglexj\DaVinciFlow\dist\DaVinciFlow-Setup-0.3.0.exe
```

El ejecutable de escritorio se compila aparte (PyInstaller, modo `onedir`):

```
D:\Proyectos\biglexj\DaVinciFlow\packaging\windows\build\dist\DaVinciFlow\
    DaVinciFlow.exe        8 985 759 bytes
    _internal\             (~64 MB, incluye el cliente de Flet)
```

## 3. Qué se comprobó

| # | Comprobación | Resultado | Evidencia |
| --- | --- | --- | --- |
| 1 | La compilación termina sin errores | **OK** | salida de ISCC arriba |
| 2 | `version.iss` se regenera con la versión real | **OK** | `#define MyAppVersion "0.3.0"` |
| 3 | Los archivos de empaquetado siguen versionados | **OK** | `git check-ignore` sobre los 9 archivos: ninguno ignorado |
| 4 | Pantalla de entrada con el diseño 2.0 | **OK** | `01-entrada-oscuro.png` |
| 5 | Nombre de la app completo en la cabecera | **OK** | `nombre-largo.png` (52 caracteres, sin recorte) |
| 6 | Icono de la app centrado en su contenedor | **OK** | `01-entrada-oscuro.png` |
| 7 | Tema oscuro | **OK** | `tema-dark.png` |
| 8 | Tema claro | **OK** | `tema-light.png` |
| 9 | Foco inicial en el campo de ruta, con cursor visible | **OK** | `GetGUIThreadInfo`: `foco=TEdit … caret=si` |
| 10 | Tab: ruta → carpeta | **OK** | `GetGUIThreadInfo`: `foco=TBitmapButton 'Elegir carpeta de instalación'` |
| 11 | Shift+Tab: carpeta → ruta | **OK** | `GetGUIThreadInfo`: `foco=TEdit … caret=si` |
| 12 | Ciclo completo ruta → carpeta → instalar → ruta | **OK** | `06-ciclo-tab.png` + lecturas de foco |
| 13 | Enter en «carpeta» abre el selector de verdad | **OK** | `04-selector-carpeta.png`, `12-selector-abierto.png` (diálogo nativo `#32770` «Selecciona la ubicación de instalación») |
| 14 | Enter instala (progreso nativo) | **OK** | `07-progreso.png` («Instalando…» con barra) |
| 15 | Pantalla de éxito nativa | **OK** | `08-exito.png` («Instalación completada») |
| 16 | Foco en «Finalizar» al llegar al éxito | **OK** | `GetGUIThreadInfo`: `foco=TNewButton '&Finalizar'` |
| 17 | Enter en «Finalizar» cierra el instalador | **OK** | el proceso del setup termina y arranca la app |
| 18 | La app instalada **abre** | **OK** | `09-app-instalado.png`, `10-app-tras-reinstalar.png` (ventana «DaVinci Flow — Editor y recursos» con el icono oficial) |
| 19 | La X cancela | **OK** | diálogo «Salir de la Instalación» → «Sí» → el setup cierra y **no** modifica la instalación (371 archivos antes y después) |
| 20 | Desinstalación limpia | **OK** | `unins000.exe /VERYSILENT` → exit 0; se borran carpeta, clave de registro y accesos directos |
| 21 | La desinstalación **no** borra datos del usuario | **OK** | `%USERPROFILE%\.davinci_flow\` intacto: `config.json`, `editorial_preferences.json`, 13 registros, 2 logs |
| 22 | Reinstalación con el mismo `AppId` sin instalación paralela | **OK** | una sola carpeta (`…\Programs\DaVinciFlow`) y una sola clave (`{4E7B2A63-…}_is1`) |
| 23 | La ruta de instalación es editable | **PARCIAL** | ver §4 |
| 24 | Escalas 125 % / 150 % / 200 % | **PENDIENTE** | ver §4 |

## 4. Pendientes y su motivo

### 4.1 Escritura en el campo de ruta (parcial)

Comprobado:

- El campo es un control `TEdit` real (no un rótulo), con foco y cursor.
- Una ruta **no predeterminada** escrita en él gobernó una instalación real de
  esta misma sesión: el instalador terminó en
  `…\packaging\windows\build\validation\instalacion-prueba` y el registro
  guardó `InstallLocation` con esa misma ruta (el valor predeterminado es
  `{localappdata}\Programs\DaVinciFlow`). El selector de carpeta se abrió
  además en esa ruta editada (`04-selector-carpeta.png`).

No reproducido de forma aislada: **escribir con teclado sintético** dentro del
campo. En esta máquina compartida el primer plano lo roban otros procesos
(instaladores de otros agentes) y la inyección de teclas acaba en la ventana
equivocada. Se probaron cuatro vías —`WM_CHAR` dirigido, `Ctrl+A`/`Ctrl+V` con
portapapeles, teclas reales con `SendInput` y clic real del ratón dentro del
campo— y ninguna dejó texto nuevo mientras otra ventana tenía el primer plano.
Con el primer plano tomado a la fuerza (`AttachThreadInput` al hilo del
primer plano) la ventana sí queda delante y el foco sí está en el `TEdit`, pero
la entrada sintética sigue sin llegar al control.

**Es una limitación del entorno de prueba, no del instalador**: el campo es un
`TEdit` estándar de VCL y la ruta escrita se respeta (evidencia del punto 23).
Queda pendiente una comprobación manual con teclado físico.

### 4.2 Escalas del sistema (125 %, 150 %, 200 %)

**PENDIENTE.** Cambiar la escala de Windows exige reiniciar sesión, y en este
momento hay otros agentes ejecutando instaladores en el mismo escritorio
(`Instalar Luna Fetch` activo durante la sesión). Interrumpirles no es
aceptable, así que la prueba queda sin hacer.

Lo que sí está comprobado es que la plantilla escala **una sola vez** todas
las medidas con `ScaleX`/`ScaleY`, incluida el área cliente (560 × 444 lógicos),
y que a 100 % el diseño coincide con el contrato visual. Que el código escale
no prueba esos tres casos: siguen pendientes.

### 4.3 Nombre largo

Comprobado físicamente con un nombre de **52 caracteres**
(`DaVinci Flow Editor y Recursos Avanzados para Video`, `nombre-largo.png`):

- La cabecera muestra el nombre **completo**, con el cuerpo de fuente reducido
  automáticamente (sin recorte a media palabra).
- La descripción pasa a dos líneas sin salirse de la tarjeta.
- El botón «Instalar …» muestra el nombre completo con el cuerpo reducido.

## 5. Cómo se hizo el control del teclado

En una máquina con varios instaladores a la vez, la inyección de teclas es poco
fiable. Lo que funcionó:

- Identificar la ventana propia por **proceso** (el `.tmp` que Inno extrae a
  partir del setup lanzado) y por **título exacto**; nunca por título suelto.
- Fijar el foco real con `AttachThreadInput` + `SetFocus` sobre el control
  concreto (`TEdit`, `TBitmapButton`), en lugar de `WizardForm.ActiveControl`.
- Enviar la tecla al control enfocado con `PostMessage` (no bloqueante: Enter
  sobre «carpeta» abre un diálogo modal y `SendMessage` se quedaría colgado).
- **Mantener el modificador físico con `SendInput`** mientras llega el mensaje
  de tecla, porque VCL lee el estado real del teclado (`GetKeyState`).
- Leer el foco con `GetGUIThreadInfo` del hilo del instalador, no del primer
  plano, que puede ser de otra aplicación.

Se descartaron tres intentos previos: `SendInput` con `KEYEVENTF_UNICODE` sin
tener el primer plano, `WM_CHAR` dirigido al `TEdit` y `BM_CLICK` sobre el
botón «Seleccionar carpeta» del diálogo (cierra el diálogo pero el motor lo
interpreta como cancelación).

## 6. Correcciones aplicadas durante la validación

1. **El cliente de Flet se quedaba sin ventana en el ejecutable final.** En
   modo `windowed` (sin consola) PyInstaller deja `sys.stdout` y `sys.stderr`
   a `None`, y Flet los usa: el cliente arrancaba pero la ventana no se
   mostraba nunca. Se corrigió en `packaging\windows\launcher\DaVinciFlow.py`
   redirigiendo ambas salidas al log de la app
   (`%USERPROFILE%\.davinci_flow\logs\desktop-bundled.log`).
2. **Faltaban los datos del paquete `flet`** en el bundle (fatal
   `FileNotFoundError` al leer `flet\controls\material\icons.json`). Se
   resolvió con `collect_all` para `flet`, `flet_desktop` y `davinci_flow` en
   `DaVinciFlow.spec`.
3. **`AppId` con GUID**: `{#MyAppId}` hace que Inno Setup interprete el GUID
   entre llaves como una constante de `[Setup]` y falla la compilación
   (*Unknown constant*). La forma correcta es `AppId={{#MyAppId}` (doble llave
   solo en la apertura).
4. **`ignoreversion` retirado** de los `[Files]`: los binarios internos del
   bundle no llevan versión y no se reescribirían en una actualización.

## 7. Residuos que deja la instalación

- `%USERPROFILE%\.flet\client\flet-desktop-full-0.86.5\`: caché del cliente de
  Flet (comportamiento propio de Flet). **No** es dato del usuario y el
  desinstalador no la borra.
- `%USERPROFILE%\.davinci_flow\`: datos del usuario (configuración,
  preferencias, registros, logs). **No** los borra el desinstalador.
