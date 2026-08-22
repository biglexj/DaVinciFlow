"""Registro y auditoría de elementos generados para idempotencia y reversión."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from davinci_flow.errors import DaVinciFlowError


class GenerationRecordError(DaVinciFlowError):
    """Error relacionado con el registro histórico de generaciones."""


@dataclass(frozen=True, slots=True)
class GenerationItemRecord:
    """Registro individual de un clip o título insertado en la línea de tiempo."""

    item_id: str
    block_id: str
    role: str
    track_type: str  # "video", "audio"
    track_index: int
    track_name: str
    start_frame: float
    end_frame: float
    content_text: str
    status: str = "applied"  # "planned", "applied", "replaced", "reverted", "missing"
    native_item_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serializa el registro del elemento."""
        return {
            "item_id": self.item_id,
            "block_id": self.block_id,
            "role": self.role,
            "track_type": self.track_type,
            "track_index": self.track_index,
            "track_name": self.track_name,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "content_text": self.content_text,
            "status": self.status,
            "native_item_id": self.native_item_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationItemRecord":
        """Instancia un GenerationItemRecord a partir de un diccionario."""
        return cls(
            item_id=str(data["item_id"]),
            block_id=str(data["block_id"]),
            role=str(data["role"]),
            track_type=str(data["track_type"]),
            track_index=int(data["track_index"]),
            track_name=str(data["track_name"]),
            start_frame=float(data["start_frame"]),
            end_frame=float(data["end_frame"]),
            content_text=str(data["content_text"]),
            status=str(data.get("status", "applied")),
            native_item_id=(
                str(data["native_item_id"])
                if data.get("native_item_id") is not None
                else None
            ),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True, slots=True)
class GenerationExecutionRecord:
    """Registro global de una ejecución que agrupa todos los elementos generados."""

    execution_id: str
    plan_id: str
    source_hash: str
    project_name: str
    timeline_name: str
    theme_name: str
    profile_name: str
    items: tuple[GenerationItemRecord, ...]
    status: str = "completed"  # "completed", "partial", "reverted"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def item_count(self) -> int:
        """Cantidad total de clips generados en esta ejecución."""
        return len(self.items)

    @property
    def active_item_count(self) -> int:
        """Cantidad de clips actualmente aplicados."""
        return sum(1 for item in self.items if item.status == "applied")

    def to_dict(self) -> dict[str, Any]:
        """Serializa la ejecución a diccionario."""
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "source_hash": self.source_hash,
            "project_name": self.project_name,
            "timeline_name": self.timeline_name,
            "theme_name": self.theme_name,
            "profile_name": self.profile_name,
            "status": self.status,
            "created_at": self.created_at,
            "items": [item.to_dict() for item in self.items],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convierte la ejecución a JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationExecutionRecord":
        """Reconstruye una ejecución desde un diccionario."""
        raw_items = data.get("items", [])
        items = tuple(GenerationItemRecord.from_dict(i) for i in raw_items)
        return cls(
            execution_id=str(data["execution_id"]),
            plan_id=str(data["plan_id"]),
            source_hash=str(data["source_hash"]),
            project_name=str(data["project_name"]),
            timeline_name=str(data["timeline_name"]),
            theme_name=str(data["theme_name"]),
            profile_name=str(data["profile_name"]),
            status=str(data.get("status", "completed")),
            created_at=str(data.get("created_at", "")),
            items=items,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "GenerationExecutionRecord":
        """Instancia desde JSON."""
        try:
            return cls.from_dict(json.loads(json_str))
        except Exception as err:
            raise GenerationRecordError(f"Error al deserializar GenerationExecutionRecord: {err}") from err

    def save_to_file(self, filepath: str | Path) -> None:
        """Guarda el registro de ejecución en disco."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, filepath: str | Path) -> "GenerationExecutionRecord":
        """Carga el registro de ejecución desde disco."""
        path = Path(filepath)
        if not path.is_file():
            raise GenerationRecordError(f"El registro de ejecución no existe: {path}")
        return cls.from_json(path.read_text(encoding="utf-8"))
