"""Entrada ligera compartida por el menú de Resolve y la consola."""

from davinci_flow.user_data import checkout_root, user_data_dir
import os
from pathlib import Path
import shutil
import subprocess


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


def launch_desktop():
    root = checkout_root()
    if root is None:
        raise RuntimeError("Abre DaVinci Flow con mise dev desde la carpeta del repositorio.")
    exe_name = 'davinci-flow-gpui.exe' if os.name == 'nt' else 'davinci-flow-gpui'
    candidates = [
        root / 'target' / 'release' / exe_name,
        root / 'target' / 'debug' / exe_name,
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
    manifest = root / 'Cargo.toml'
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
    raise RuntimeError("Compila DaVinci Flow con mise build para abrirlo desde Resolve.")
