"""Punto de entrada del ejecutable de escritorio de DaVinci Flow.

Este archivo es el script de entrada que PyInstaller convierte en
`DaVinciFlow.exe`. No contiene logica de la aplicacion: solo prepara las
rutas de los paquetes del proyecto y corrige la ruta de los recursos de
marca, que en modo congelado no coincide con la del repositorio.

Reglas:
- No se modifica codigo de produccion (`src/` ni `src-flet/`).
- Los datos del usuario nunca se escriben junto al ejecutable: el registro
  de fallos va a `%USERPROFILE%\.davinci_flow\logs`.
"""

import sys
import traceback
from pathlib import Path


def _base_dir() -> Path:
    """Directorio base de los recursos empaquetados."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _prepare_import_paths(base: Path) -> None:
    """En modo congelado los modulos ya vienen empaquetados; en modo fuente
    se anaden `src` y `src-flet` al `sys.path`."""
    for relative in ("src", "src-flet"):
        candidate = base / relative
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


def _log_failure(exc: BaseException) -> None:
    """Deja rastro del fallo sin depender de una consola visible."""
    try:
        log_dir = Path.home() / ".davinci_flow" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "desktop-bundled.log").open("a", encoding="utf-8") as handle:
            handle.write("---- DaVinci Flow (empaquetado) ----\n")
            handle.write(traceback.format_exc())
            handle.write("\n")
    except Exception:
        pass


def _prepare_streams() -> None:
    """En un ejecutable sin consola (PyInstaller en modo `windowed`) las
    salidas estandar valen None. Flet las usa para escribir mensajes y el
    cliente de escritorio se queda oculto sin ventana. Se redirigen al log."""
    if not getattr(sys, "frozen", False):
        return
    try:
        log_dir = Path.home() / ".davinci_flow" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = (log_dir / "desktop-bundled.log").open("a", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = stream
        if sys.stderr is None:
            sys.stderr = stream
    except Exception:
        pass


def main() -> None:
    _prepare_streams()
    base = _base_dir()
    _prepare_import_paths(base)

    import app.app as desktop_app

    branding = base / "assets" / "branding" / "icons"
    if branding.is_dir():
        # `app.app` resuelve los recursos de marca desde la raiz del
        # repositorio; en modo congelado la ruta valida es la del paquete.
        desktop_app.BRANDING = branding

    desktop_app.open_desktop()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        _log_failure(sys.exc_info()[1])
        raise
