"""Entrada ligera compartida por el menú de Resolve y la consola."""

import os
from pathlib import Path
import subprocess
import sys


def launch_desktop():
    root = Path(__file__).resolve().parents[3]
    executable = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not executable.is_file():
        executable = Path(sys.executable)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root / 'src') + os.pathsep + str(root / 'src-flet') + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUTF8'] = '1'
    log_dir = Path.home() / '.davinci_flow/logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'desktop.log').open('a', encoding='utf-8') as log:
        return subprocess.Popen([str(executable), str(root / 'src-flet' / 'main.py')], cwd=root, env=env,
            stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
