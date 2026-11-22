"""Entrada ligera compartida por el menú de Resolve y la consola."""

from davinci_flow.user_data import user_data_dir
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _rust_env() -> dict[str, str]:
    env = os.environ.copy()
    home = Path.home()
    extra_bins = [
        home / ".rustup" / "toolchains" / "stable-x86_64-pc-windows-gnullvm" / "bin",
        home / ".rustup" / "toolchains" / "stable-x86_64-pc-windows-msvc" / "bin",
        home / ".cargo" / "bin",
    ]
    existing = [str(p) for p in extra_bins if p.is_dir()]
    if existing:
        env["PATH"] = os.pathsep.join(existing + [env.get("PATH", "")])
    return env


def launch_flet():
    root = Path(__file__).resolve().parents[3]
    executable = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not executable.is_file():
        executable = Path(sys.executable)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root / 'src') + os.pathsep + str(root / 'src-flet') + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUTF8'] = '1'
    log_dir = user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'desktop.log').open('a', encoding='utf-8') as log:
        return subprocess.Popen(
            [str(executable), str(root / 'src-flet' / 'main.py')],
            cwd=root,
            env=env,
            stdout=log,
            stderr=log,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )


def launch_desktop(prefer_flet: bool = False):
    if prefer_flet or os.environ.get('DAVINCIFLOW_UI', '').lower() == 'flet':
        return launch_flet()
    root = Path(__file__).resolve().parents[3]
    exe_name = 'davinci-flow-gpui.exe' if os.name == 'nt' else 'davinci-flow-gpui'
    candidates = [
        root / 'src-gpui' / 'target' / 'release' / exe_name,
        root / 'src-gpui' / 'target' / 'debug' / exe_name,
    ]
    gpui_exe = next((p for p in candidates if p.is_file()), None)
    env = _rust_env()
    log_dir = user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if gpui_exe is not None:
        with (log_dir / 'desktop-gpui.log').open('a', encoding='utf-8') as log:
            return subprocess.Popen(
                [str(gpui_exe)],
                cwd=root,
                env=env,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
    cargo = shutil.which('cargo', path=env.get('PATH'))
    manifest = root / 'src-gpui' / 'Cargo.toml'
    if cargo and manifest.is_file():
        with (log_dir / 'desktop-gpui.log').open('a', encoding='utf-8') as log:
            return subprocess.Popen(
                [cargo, 'run', '--manifest-path', str(manifest), '--locked'],
                cwd=root,
                env=env,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
    return launch_flet()
