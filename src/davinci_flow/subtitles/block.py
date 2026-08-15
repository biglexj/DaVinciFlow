"""Modelo de bloque de subtítulo dinámico y jerarquía de capas."""

from dataclasses import dataclass
from typing import Any

from davinci_flow.subtitles.model import SubtitleCue


@dataclass(frozen=True, slots=True)
class CaptionBlock:
    """Bloque estructurado con trazabilidad y roles visuales (contexto, principal, acento)."""

    id: str
    source_cues: tuple[SubtitleCue, ...]
    start_frame: float
    end_frame: float
    original_text: str
    normalized_text: str
    main_text: str
    context_text: str | None = None
    accent_text: str | None = None
    intent: str = "statement"
    confidence: float = 1.0
    reason: str = "Asignación directa."
    style_preset: str | None = None
    sfx_proposal: str | None = None
    is_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("El identificador del bloque no puede estar vacío.")
        if not self.main_text.strip():
            raise ValueError("El texto principal del bloque no puede estar vacío.")
        if self.start_frame < 0:
            raise ValueError("El fotograma inicial no puede ser negativo.")
        if self.end_frame < self.start_frame:
            raise ValueError("El fotograma final no puede preceder al inicial.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("La confianza de clasificación debe estar comprendida entre 0.0 y 1.0.")

    @property
    def duration_frames(self) -> float:
        """Duración total del bloque en fotogramas."""
        return self.end_frame - self.start_frame

    @property
    def layer_count(self) -> int:
        """Cantidad de capas activas (1, 2 o 3)."""
        count = 1  # main_text siempre está presente
        if self.context_text and self.context_text.strip():
            count += 1
        if self.accent_text and self.accent_text.strip():
            count += 1
        return count

    @property
    def active_layers(self) -> tuple[str, ...]:
        """Tupla con los nombres de las capas activas en orden de jerarquía."""
        layers: list[str] = []
        if self.context_text and self.context_text.strip():
            layers.append("context")
        layers.append("main")
        if self.accent_text and self.accent_text.strip():
            layers.append("accent")
        return tuple(layers)

    @property
    def reconstructed_text(self) -> str:
        """Reconstrucción del texto a partir de las capas activas."""
        parts: list[str] = []
        if self.context_text and self.context_text.strip():
            parts.append(self.context_text.strip())
        parts.append(self.main_text.strip())
        if self.accent_text and self.accent_text.strip():
            parts.append(self.accent_text.strip())
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el bloque a un diccionario estándar."""
        return {
            "id": self.id,
            "source_cues": [
                {
                    "text": cue.text,
                    "start_frame": cue.start_frame,
                    "end_frame": cue.end_frame,
                    "track_index": cue.track_index,
                }
                for cue in self.source_cues
            ],
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "context_text": self.context_text,
            "main_text": self.main_text,
            "accent_text": self.accent_text,
            "intent": self.intent,
            "confidence": self.confidence,
            "reason": self.reason,
            "style_preset": self.style_preset,
            "sfx_proposal": self.sfx_proposal,
            "is_enabled": self.is_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptionBlock":
        """Instancia un CaptionBlock a partir de un diccionario serializado."""
        raw_cues = data.get("source_cues", [])
        cues = tuple(
            SubtitleCue(
                text=str(c["text"]),
                start_frame=float(c["start_frame"]),
                end_frame=float(c["end_frame"]),
                track_index=int(c["track_index"]),
            )
            for c in raw_cues
        )
        return cls(
            id=str(data["id"]),
            source_cues=cues,
            start_frame=float(data["start_frame"]),
            end_frame=float(data["end_frame"]),
            original_text=str(data["original_text"]),
            normalized_text=str(data["normalized_text"]),
            context_text=str(data["context_text"]) if data.get("context_text") is not None else None,
            main_text=str(data["main_text"]),
            accent_text=str(data["accent_text"]) if data.get("accent_text") is not None else None,
            intent=str(data.get("intent", "statement")),
            confidence=float(data.get("confidence", 1.0)),
            reason=str(data.get("reason", "Asignación directa.")),
            style_preset=str(data["style_preset"]) if data.get("style_preset") is not None else None,
            sfx_proposal=str(data["sfx_proposal"]) if data.get("sfx_proposal") is not None else None,
            is_enabled=bool(data.get("is_enabled", True)),
        )
