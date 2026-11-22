"""Datos separados para el ejecutable instalado y cada checkout de desarrollo."""

import hashlib
from pathlib import Path
import sys


def is_development() -> bool:
    root = Path(__file__).resolve().parents[2]
    return not getattr(sys, 'frozen', False) and (root / 'pyproject.toml').is_file()


def user_data_dir() -> Path:
    base = Path.home() / '.davinci_flow'
    if is_development():
        root = str(Path(__file__).resolve().parents[2]).casefold()
        key = hashlib.sha256(root.encode()).hexdigest()[:16]
        return base / 'development' / key
    return base
