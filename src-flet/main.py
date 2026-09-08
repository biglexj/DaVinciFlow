"""Punto de entrada principal para DaVinci Flow Desktop (Flet)."""

import os
from pathlib import Path
import sys

# Asegurar que la raíz del proyecto y src/ estén en sys.path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SRC_FLET = ROOT / "src-flet"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SRC_FLET) not in sys.path:
    sys.path.insert(0, str(SRC_FLET))

from app.app import open_desktop


def main():
    open_desktop()


if __name__ == "__main__":
    main()
