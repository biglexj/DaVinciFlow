; ---------------------------------------------------------------------------
; identity.iss - identidad de DaVinci Flow para el instalador de Windows.
; Mantener MyAppId estable entre versiones: es la clave de actualizacion.
; ---------------------------------------------------------------------------

; Nombre visible de la aplicacion (el que ve el usuario en el titulo del
; asistente y en el menu de inicio).
#ifndef MyAppName
  #define MyAppName "DaVinci Flow"
#endif

; Identidad de actualizacion, propia y estable de DaVinci Flow.
; GUID generado para este proyecto; no reutilizar el de la plantilla ni el de
; ninguna otra app de Biglex.
#ifndef MyAppId
  #define MyAppId "{4E7B2A63-1C05-4F3D-9A28-6D5B0C91F4E2}"
#endif

; Carpeta de instalacion: {localappdata}\Programs\DaVinciFlow
#ifndef MyAppDirectory
  #define MyAppDirectory "DaVinciFlow"
#endif

; Ejecutable real del artefacto de escritorio (PyInstaller, modo onedir).
#ifndef MyAppExe
  #define MyAppExe "DaVinciFlow.exe"
#endif

; Icono oficial de la aplicacion (copia de
; assets\branding\icons\icon-windows.ico, con transparencia y 256x256).
#ifndef MyAppIcon
  #define MyAppIcon "DaVinciFlow.ico"
#endif

; Tema automatico: claro u oscuro segun el de Windows.
#ifndef MyAppTheme
  #define MyAppTheme "dynamic"
#endif

; Carpeta con el artefacto de escritorio empaquetado, relativa a esta carpeta.
; La prepara scripts/packaging/Build-Installer.ps1 (salida onedir de
; PyInstaller, recreada limpia en cada compilacion).
#ifndef MyAppPayload
  #define MyAppPayload "build\dist\DaVinciFlow"
#endif

#ifndef MyAppSubtitle
  #define MyAppSubtitle "De la transcripción a la edición."
#endif
