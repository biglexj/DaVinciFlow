"""Materialización ligera de los SFX originales incluidos con DaVinci Flow."""

from __future__ import annotations

import math
import os
import random
import struct
import wave
from collections.abc import Callable
from pathlib import Path

from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS

SAMPLE_RATE = 44_100


def default_sfx_root() -> Path:
    """Devuelve la carpeta persistente de recursos generados para el usuario actual."""
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".davinci-flow"
    return base / "DaVinciFlow" / "assets"


def _write_wav(path: Path, duration: float, sampler: Callable[[int, float], float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(round(duration * SAMPLE_RATE)))
    samples = bytearray()
    for index in range(frame_count):
        time_s = index / SAMPLE_RATE
        value = max(-1.0, min(1.0, sampler(index, time_s)))
        samples.extend(struct.pack("<h", int(round(value * 32767))))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples)


def _whoosh(duration: float) -> Callable[[int, float], float]:
    rng = random.Random(21)
    previous = 0.0

    def sample(_index: int, time_s: float) -> float:
        nonlocal previous
        phase = min(1.0, time_s / duration)
        envelope = math.sin(math.pi * phase) ** 1.7
        noise = rng.uniform(-1.0, 1.0)
        smoothing = 0.04 + 0.16 * phase
        previous += (noise - previous) * smoothing
        tone = math.sin(2.0 * math.pi * (280.0 + 520.0 * phase) * time_s)
        return (previous * 0.48 + tone * 0.08) * envelope

    return sample


def _pop(duration: float) -> Callable[[int, float], float]:
    def sample(_index: int, time_s: float) -> float:
        phase = min(1.0, time_s / duration)
        envelope = math.exp(-15.0 * phase)
        frequency = 330.0 - 170.0 * phase
        return math.sin(2.0 * math.pi * frequency * time_s) * envelope * 0.62

    return sample


def _bell(duration: float) -> Callable[[int, float], float]:
    def sample(_index: int, time_s: float) -> float:
        phase = min(1.0, time_s / duration)
        envelope = math.exp(-4.8 * phase)
        partials = (
            math.sin(2.0 * math.pi * 880.0 * time_s) * 0.38
            + math.sin(2.0 * math.pi * 1320.0 * time_s) * 0.19
            + math.sin(2.0 * math.pi * 2112.0 * time_s) * 0.08
        )
        return partials * envelope

    return sample


def _click(duration: float) -> Callable[[int, float], float]:
    rng = random.Random(7)

    def sample(_index: int, time_s: float) -> float:
        phase = min(1.0, time_s / duration)
        envelope = math.exp(-28.0 * phase)
        return (rng.uniform(-1.0, 1.0) * 0.35 + math.sin(2.0 * math.pi * 1800.0 * time_s) * 0.2) * envelope

    return sample


_SAMPLERS = {
    "sfx_whoosh_clean_01": _whoosh,
    "sfx_pop_subtle_01": _pop,
    "sfx_bell_chime_01": _bell,
    "sfx_click_tech_01": _click,
}


def ensure_builtin_sfx_assets(root: str | Path | None = None) -> dict[str, Path]:
    """Crea una vez los WAV originales incluidos y devuelve sus rutas verificadas."""
    asset_root = Path(root) if root is not None else default_sfx_root()
    resolved: dict[str, Path] = {}

    for descriptor in DEFAULT_SFX_ASSETS:
        path = asset_root / descriptor.relative_path
        is_current = False
        if path.is_file() and path.stat().st_size >= 128:
            try:
                with wave.open(str(path), "rb") as wav_file:
                    is_current = (
                        wav_file.getframerate() == SAMPLE_RATE
                        and wav_file.getnchannels() == 1
                        and wav_file.getsampwidth() == 2
                    )
            except (OSError, wave.Error):
                is_current = False
        if not is_current:
            factory = _SAMPLERS[descriptor.id]
            _write_wav(path, descriptor.duration_seconds, factory(descriptor.duration_seconds))
        resolved[descriptor.id] = path

    return resolved
