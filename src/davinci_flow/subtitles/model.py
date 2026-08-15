"""Modelo de subtítulo independiente de DaVinci Resolve."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    """Bloque de subtítulo situado en una pista y un intervalo de fotogramas."""

    text: str
    start_frame: float
    end_frame: float
    track_index: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("El texto del subtítulo no puede estar vacío.")
        if self.start_frame < 0:
            raise ValueError("El fotograma inicial no puede ser negativo.")
        if self.end_frame < self.start_frame:
            raise ValueError("El fotograma final no puede preceder al inicial.")
        if self.track_index < 1:
            raise ValueError("El índice de pista debe comenzar en 1.")

    @property
    def duration_frames(self) -> float:
        """Duración del bloque en fotogramas."""

        return self.end_frame - self.start_frame
