"""Retorno nativo: valida y guarda el código de Aurora para GPUI."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from davinci_flow.voice.account import accept_callback

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(2)
    try:
        accept_callback(sys.argv[1])
    except Exception:
        raise SystemExit(1)
