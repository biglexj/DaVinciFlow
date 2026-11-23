"""Datos separados para el ejecutable instalado y cada checkout de desarrollo."""

import hashlib
from pathlib import Path
import sys


def checkout_root() -> Path | None:
    if getattr(sys, 'frozen', False):
        return None
    source = Path(__file__).resolve()
    return next((parent for parent in source.parents if (
        (parent / 'Cargo.toml').is_file()
        and (parent / 'compat/python/pyproject.toml').is_file()
    )), None)


def is_development() -> bool:
    return checkout_root() is not None


def user_data_dir() -> Path:
    base = Path.home() / '.davinci_flow'
    root = checkout_root()
    if root is not None:
        key = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:16]
        return base / 'development' / key
    return base
