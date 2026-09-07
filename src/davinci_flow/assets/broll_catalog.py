"""Catálogo y escáner de recursos de apoyo (B-Rolls y SFX) del usuario."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Sequence

from davinci_flow.errors import DaVinciFlowError


class AssetCatalogError(DaVinciFlowError):
    """Error al escanear o procesar la biblioteca de assets."""


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a"}


def _extract_tags_from_path(file_path: Path, root_dir: Path | None = None) -> tuple[str, ...]:
    """Extrae palabras clave y etiquetas semánticas a partir de la ruta y nombre del archivo."""
    parts_to_inspect: list[str] = []
    if root_dir is not None:
        try:
            rel = file_path.relative_to(root_dir)
            parts_to_inspect.extend(rel.parts)
        except ValueError:
            parts_to_inspect.append(file_path.stem)
    else:
        parts_to_inspect.append(file_path.stem)

    raw_tokens: list[str] = []
    for part in parts_to_inspect:
        name_no_ext = Path(part).stem
        cleaned = re.sub(r"[_\-–—./\\]+", " ", name_no_ext)
        words = re.findall(r"[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ]+", cleaned)
        raw_tokens.extend(words)

    stop_words = {
        "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en",
        "para", "por", "con", "a", "del", "al", "video", "clip", "audio", "sfx", "asset",
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "broll",
    }

    seen: set[str] = set()
    result: list[str] = []
    for token in raw_tokens:
        tok_low = token.lower().strip()
        if len(tok_low) >= 2 and tok_low not in stop_words and tok_low not in seen:
            seen.add(tok_low)
            result.append(tok_low)

    return tuple(result)


@dataclass(frozen=True, slots=True)
class BRollAsset:
    """Descriptor de un clip de vídeo o sonido de apoyo disponible."""

    id: str
    name: str
    file_path: str
    asset_type: str  # "video" | "audio"
    tags: tuple[str, ...]
    relative_path: str = ""
    duration_seconds: float = 0.0

    def matches_query(self, query_terms: Sequence[str]) -> float:
        """Calcula una puntuación de coincidencia semántica basada en los tags."""
        if not query_terms or not self.tags:
            return 0.0

        score = 0.0
        normalized_queries = [q.lower().strip() for q in query_terms if q.strip()]
        for q in normalized_queries:
            for tag in self.tags:
                if q == tag:
                    score += 2.0
                elif q in tag or tag in q:
                    score += 1.0
        return score


@dataclass(frozen=True, slots=True)
class BRollProposal:
    """Propuesta de inserción de un recurso de B-Roll o audio contextual."""

    block_index: int
    asset: BRollAsset
    start_frame: float
    end_frame: float
    target_track: str = "DF_BROLL"
    reason: str = ""
    score: float = 1.0


@dataclass
class AssetCollection:
    """Colección indexada de recursos de apoyo con utilidades de búsqueda."""

    assets: tuple[BRollAsset, ...] = field(default_factory=tuple)

    @property
    def total_count(self) -> int:
        return len(self.assets)

    @property
    def video_assets(self) -> list[BRollAsset]:
        return [a for a in self.assets if a.asset_type == "video"]

    @property
    def audio_assets(self) -> list[BRollAsset]:
        return [a for a in self.assets if a.asset_type == "audio"]

    def find_best_match(
        self,
        query_terms: Sequence[str],
        asset_type: str = "video",
        min_score: float = 1.0,
    ) -> tuple[BRollAsset | None, float]:
        """Busca el asset que mejor coincida con los términos proporcionados."""
        candidates = self.video_assets if asset_type == "video" else self.audio_assets
        best_asset: BRollAsset | None = None
        best_score = 0.0

        for asset in candidates:
            score = asset.matches_query(query_terms)
            if score > best_score and score >= min_score:
                best_score = score
                best_asset = asset

        return best_asset, best_score


def scan_assets_directory(directory_path: str | Path) -> AssetCollection:
    """Escanea recursivamente una carpeta en busca de vídeos y sonidos de apoyo."""
    path = Path(directory_path).resolve()
    if not path.exists() or not path.is_dir():
        return AssetCollection()

    found_assets: list[BRollAsset] = []
    idx = 1

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext in SUPPORTED_VIDEO_EXTENSIONS:
            asset_type = "video"
        elif ext in SUPPORTED_AUDIO_EXTENSIONS:
            asset_type = "audio"
        else:
            continue

        tags = _extract_tags_from_path(file_path, root_dir=path)
        rel_str = str(file_path.relative_to(path))
        asset_id = f"asset_{idx:03d}_{file_path.stem}"

        found_assets.append(
            BRollAsset(
                id=asset_id,
                name=file_path.name,
                file_path=str(file_path),
                asset_type=asset_type,
                tags=tags,
                relative_path=rel_str,
            )
        )
        idx += 1

    return AssetCollection(assets=tuple(found_assets))
