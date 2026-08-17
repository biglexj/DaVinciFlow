"""Lector y conversor de subtítulos en formato SRT estándar a modelos internos de DaVinci Flow."""

import re
from pathlib import Path
from typing import Sequence

from davinci_flow.errors import DaVinciFlowError
from davinci_flow.subtitles.model import SubtitleCue


class SrtParseError(DaVinciFlowError):
    """Error al parsear un archivo o contenido SRT."""


def timecode_to_frames(timecode_str: str, fps: float = 24.0) -> float:
    """Convierte una cadena de tiempo SRT (HH:MM:SS,mmm o HH:MM:SS.mmm) a fotogramas."""
    clean_tc = timecode_str.strip().replace(",", ".")
    match = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})$", clean_tc)
    if not match:
        # Intentar formato simple HH:MM:SS
        match_simple = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})$", clean_tc)
        if match_simple:
            h, m, s = (int(g) for g in match_simple.groups())
            ms = 0
        else:
            raise SrtParseError(f"Formato de código de tiempo SRT inválido: '{timecode_str}'")
    else:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        ms_str = match.group(4).ljust(3, "0")[:3]
        ms = int(ms_str)

    total_seconds = h * 3600 + m * 60 + s + (ms / 1000.0)
    return round(total_seconds * fps, 2)


def frames_to_srt_timecode(frames: float, fps: float = 24.0) -> str:
    """Convierte un número de fotogramas a formato de tiempo SRT HH:MM:SS,mmm."""
    total_seconds = max(0.0, float(frames) / max(1.0, float(fps)))
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    ms = int(round((total_seconds - int(total_seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_content(content: str, fps: float = 24.0, track_index: int = 1) -> tuple[SubtitleCue, ...]:
    """Parsea el contenido de texto de un archivo SRT y genera una tupla de SubtitleCue."""
    if not content or not content.strip():
        return ()

    # Normalizar saltos de línea
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n\s*\n", normalized)

    cues: list[SubtitleCue] = []
    tc_pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})"
    )

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        tc_line_idx = -1
        start_tc = ""
        end_tc = ""

        for idx, line in enumerate(lines):
            match = tc_pattern.search(line)
            if match:
                tc_line_idx = idx
                start_tc = match.group(1)
                end_tc = match.group(2)
                break

        if tc_line_idx == -1:
            continue

        text_lines = lines[tc_line_idx + 1 :]
        text = " ".join(text_lines).strip()
        # Limpiar etiquetas HTML básicas de formato en SRT (ej: <i>, <b>, <font>)
        clean_text = re.sub(r"<[^>]+>", "", text).strip()
        if not clean_text:
            continue

        try:
            start_frame = timecode_to_frames(start_tc, fps=fps)
            end_frame = timecode_to_frames(end_tc, fps=fps)
        except Exception:
            continue

        cues.append(
            SubtitleCue(
                text=clean_text,
                start_frame=start_frame,
                end_frame=end_frame,
                track_index=track_index,
            )
        )

    cues.sort(key=lambda c: (c.start_frame, c.end_frame))
    return tuple(cues)


def load_srt_file(filepath: str | Path, fps: float = 24.0, track_index: int = 1) -> tuple[SubtitleCue, ...]:
    """Lee un archivo SRT desde el disco y retorna la tupla de SubtitleCue."""
    p = Path(filepath)
    if not p.is_file():
        raise SrtParseError(f"No se encontró el archivo SRT en la ruta: {filepath}")

    # Intentar leer con utf-8 y fallback a latin-1
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_text(encoding="latin-1")

    return parse_srt_content(content, fps=fps, track_index=track_index)
