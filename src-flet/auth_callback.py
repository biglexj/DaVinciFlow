"""Entrada de retorno nativo del checkout; no registra códigos en logs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'src-flet')]
from davinci_flow.voice.account import accept_callback
from app.app import open_desktop

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(2)
    try:
        accept_callback(sys.argv[1])
    except Exception:
        raise SystemExit(1)
    open_desktop()
