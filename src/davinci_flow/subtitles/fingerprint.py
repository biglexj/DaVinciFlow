"""Cálculo de huellas deterministas (fingerprints) e identificadores estables."""

import hashlib
from typing import Sequence

from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.model import SubtitleCue


def compute_cues_fingerprint(cues: Sequence[SubtitleCue]) -> str:
    """Calcula una huella SHA-256 única y determinista para una secuencia de subtítulos."""
    hasher = hashlib.sha256()
    for cue in cues:
        record = f"{cue.track_index}:{cue.start_frame:.4f}:{cue.end_frame:.4f}:{cue.text}\n"
        hasher.update(record.encode("utf-8"))
    return hasher.hexdigest()


def compute_blocks_fingerprint(blocks: Sequence[CaptionBlock]) -> str:
    """Calcula una huella SHA-256 para una secuencia de bloques clasificados."""
    hasher = hashlib.sha256()
    for b in blocks:
        record = (
            f"{b.id}:{b.start_frame:.4f}:{b.end_frame:.4f}:"
            f"{b.context_text or ''}:{b.main_text}:{b.accent_text or ''}:{b.intent}\n"
        )
        hasher.update(record.encode("utf-8"))
    return hasher.hexdigest()


def generate_stable_block_id(
    track_index: int,
    order_index: int,
    start_frame: float,
    end_frame: float,
    text: str,
) -> str:
    """Genera un identificador reproducible y descriptivo para un bloque."""
    short_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"df_t{track_index}_b{order_index:04d}_{int(start_frame)}_{int(end_frame)}_{short_hash}"
