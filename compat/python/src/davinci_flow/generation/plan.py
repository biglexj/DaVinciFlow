"""Plan de generación estructurado, versionado y serializable."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from davinci_flow.errors import PlanSerializationError, PlanVersionMismatchError
from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.classifier import create_caption_block_from_cue
from davinci_flow.subtitles.fingerprint import (
    compute_cues_fingerprint,
    generate_stable_block_id,
)
from davinci_flow.subtitles.model import SubtitleCue

PLAN_SCHEMA_VERSION = "1.0.0"
SUPPORTED_MAJOR_VERSIONS = ("1",)

DEFAULT_TRACK_MAPPING = {
    "DF_CONTEXT": "DF_CONTEXT",
    "DF_MAIN": "DF_MAIN",
    "DF_ACCENT": "DF_ACCENT",
    "DF_SFX": "DF_SFX",
}


@dataclass(frozen=True, slots=True)
class GenerationPlan:
    """Plan determinista de generación que describe los elementos a crear en la línea de tiempo."""

    plan_id: str
    project_name: str
    timeline_name: str
    track_index: int
    fps: float
    width: int
    height: int
    aspect_ratio: str
    theme_name: str
    profile_name: str
    source_hash: str
    blocks: tuple[CaptionBlock, ...]
    schema_version: str = PLAN_SCHEMA_VERSION
    timeline_id: str | None = None
    start_frame: float | None = None
    end_frame: float | None = None
    track_mapping: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TRACK_MAPPING))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("El identificador del plan no puede estar vacío.")
        if not self.project_name.strip():
            raise ValueError("El nombre del proyecto no puede estar vacío.")
        if not self.timeline_name.strip():
            raise ValueError("El nombre de la línea de tiempo no puede estar vacío.")
        if self.track_index < 1:
            raise ValueError("El índice de pista debe ser 1 o superior.")
        if self.fps <= 0:
            raise ValueError("La tasa de fotogramas (fps) debe ser positiva.")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Las dimensiones de resolución deben ser positivas.")
        major_version = self.schema_version.split(".")[0]
        if major_version not in SUPPORTED_MAJOR_VERSIONS:
            raise PlanVersionMismatchError(
                f"Versión de esquema no soportada: '{self.schema_version}'. "
                f"Versiones soportadas: {SUPPORTED_MAJOR_VERSIONS}."
            )

    @property
    def block_count(self) -> int:
        """Cantidad total de bloques en el plan."""
        return len(self.blocks)

    @property
    def active_block_count(self) -> int:
        """Cantidad de bloques habilitados para generación."""
        return sum(1 for b in self.blocks if b.is_enabled)

    @property
    def layer_distribution(self) -> dict[int, int]:
        """Distribución de bloques según el número de capas (1, 2 o 3)."""
        dist = {1: 0, 2: 0, 3: 0}
        for b in self.blocks:
            count = b.layer_count
            dist[count] = dist.get(count, 0) + 1
        return dist

    def to_dict(self) -> dict[str, Any]:
        """Serializa el plan a un diccionario plano conforme al esquema."""
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "project_name": self.project_name,
            "timeline_name": self.timeline_name,
            "timeline_id": self.timeline_id,
            "track_index": self.track_index,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "theme_name": self.theme_name,
            "profile_name": self.profile_name,
            "source_hash": self.source_hash,
            "track_mapping": dict(self.track_mapping),
            "blocks": [b.to_dict() for b in self.blocks],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializa el plan a formato JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationPlan":
        """Instancia un GenerationPlan a partir de un diccionario validado."""
        try:
            version = str(data.get("schema_version", PLAN_SCHEMA_VERSION))
            major_version = version.split(".")[0]
            if major_version not in SUPPORTED_MAJOR_VERSIONS:
                raise PlanVersionMismatchError(
                    f"Incompatibilidad de versión: el plan requiere '{version}', "
                    f"pero el motor soporta versiones mayores {SUPPORTED_MAJOR_VERSIONS}."
                )

            raw_blocks = data.get("blocks", [])
            blocks = tuple(CaptionBlock.from_dict(b) for b in raw_blocks)

            return cls(
                schema_version=version,
                plan_id=str(data["plan_id"]),
                created_at=str(data.get("created_at", "")),
                project_name=str(data["project_name"]),
                timeline_name=str(data["timeline_name"]),
                timeline_id=str(data["timeline_id"]) if data.get("timeline_id") is not None else None,
                track_index=int(data["track_index"]),
                start_frame=float(data["start_frame"]) if data.get("start_frame") is not None else None,
                end_frame=float(data["end_frame"]) if data.get("end_frame") is not None else None,
                fps=float(data["fps"]),
                width=int(data["width"]),
                height=int(data["height"]),
                aspect_ratio=str(data["aspect_ratio"]),
                theme_name=str(data["theme_name"]),
                profile_name=str(data["profile_name"]),
                source_hash=str(data["source_hash"]),
                track_mapping=dict(data.get("track_mapping", DEFAULT_TRACK_MAPPING)),
                blocks=blocks,
            )
        except KeyError as err:
            raise PlanSerializationError(f"Campo requerido ausente en el plan: {err}") from err
        except Exception as err:
            if isinstance(err, (PlanSerializationError, PlanVersionMismatchError)):
                raise
            raise PlanSerializationError(f"Error al deserializar el plan: {err}") from err

    @classmethod
    def from_json(cls, json_str: str) -> "GenerationPlan":
        """Instancia un GenerationPlan a partir de una cadena JSON."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as err:
            raise PlanSerializationError(f"JSON inválido para GenerationPlan: {err}") from err
        return cls.from_dict(data)

    def save_to_file(self, filepath: str | Path) -> None:
        """Guarda el plan serializado en un archivo JSON en disco."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, filepath: str | Path) -> "GenerationPlan":
        """Carga y valida un plan de generación desde un archivo en disco."""
        path = Path(filepath)
        if not path.is_file():
            raise PlanSerializationError(f"El archivo del plan no existe: {path}")
        content = path.read_text(encoding="utf-8")
        return cls.from_json(content)


def build_generation_plan(
    project_name: str,
    timeline_name: str,
    cues: Sequence[SubtitleCue],
    track_index: int = 1,
    timeline_id: str | None = None,
    fps: float = 24.0,
    width: int = 1920,
    height: int = 1080,
    aspect_ratio: str = "16:9",
    theme_name: str = "ely",
    profile_name: str = "natural",
    track_mapping: dict[str, str] | None = None,
) -> GenerationPlan:
    """Construye un GenerationPlan completo, clasificado y con huella a partir de subtítulos."""
    source_hash = compute_cues_fingerprint(cues)
    blocks: list[CaptionBlock] = []

    for idx, cue in enumerate(cues, start=1):
        block_id = generate_stable_block_id(
            track_index=track_index,
            order_index=idx,
            start_frame=cue.start_frame,
            end_frame=cue.end_frame,
            text=cue.text,
        )
        blocks.append(create_caption_block_from_cue(cue, block_id))

    start_frame = min((c.start_frame for c in cues), default=0.0) if cues else 0.0
    end_frame = max((c.end_frame for c in cues), default=0.0) if cues else 0.0

    plan_id = f"plan_{source_hash[:12]}_{int(start_frame)}_{int(end_frame)}"

    return GenerationPlan(
        plan_id=plan_id,
        project_name=project_name,
        timeline_name=timeline_name,
        timeline_id=timeline_id,
        track_index=track_index,
        start_frame=start_frame,
        end_frame=end_frame,
        fps=fps,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        theme_name=theme_name,
        profile_name=profile_name,
        source_hash=source_hash,
        track_mapping=track_mapping or dict(DEFAULT_TRACK_MAPPING),
        blocks=tuple(blocks),
    )
