"""Catálogo oficial y descriptor de recursos sonoros (SFX) con licencias auditables."""

from dataclasses import dataclass
from typing import Mapping, Sequence

from davinci_flow.errors import DaVinciFlowError


class SFXCatalogError(DaVinciFlowError):
    """Error al consultar o validar un recurso sonoro."""


@dataclass(frozen=True, slots=True)
class AssetDescriptor:
    """Descriptor auditable de un recurso de audio con autoría, licencia y restricciones."""

    id: str
    name: str
    category: str
    relative_path: str
    duration_seconds: float
    recommended_gain_db: float = -12.0
    cooldown_frames: float = 72.0  # 3 segundos a 24 fps
    allowed_intents: tuple[str, ...] = ("emphasis", "question", "statement")
    prohibited_intents: tuple[str, ...] = ()
    author: str = "DaVinci Flow"
    license: str = "MIT / Libre de regalías"
    source: str = "Generador procedural de DaVinci Flow"

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("El identificador del SFX no puede estar vacío.")
        if not self.name.strip():
            raise ValueError("El nombre del recurso sonoro no puede estar vacío.")
        if not self.category.strip():
            raise ValueError("La categoría del recurso sonoro no puede estar vacía.")
        if not self.author.strip() or not self.license.strip() or not self.source.strip():
            raise SFXCatalogError(f"El recurso '{self.id}' carece de metadatos de autoría o licencia completos.")
        if self.duration_seconds <= 0:
            raise ValueError("La duración del recurso debe ser positiva.")


# Biblioteca inicial de efectos de sonido incorporada
DEFAULT_SFX_ASSETS: Sequence[AssetDescriptor] = (
    AssetDescriptor(
        id="sfx_whoosh_clean_01",
        name="Whoosh Limpio",
        category="whoosh",
        relative_path="sfx/whooshes/whoosh_clean_01.wav",
        duration_seconds=0.45,
        recommended_gain_db=-14.0,
        cooldown_frames=60.0,
        allowed_intents=("emphasis", "statement", "exclamation"),
        prohibited_intents=(),
        author="DaVinci Flow",
        license="MIT / Libre de regalías",
        source="Generador procedural de DaVinci Flow",
    ),
    AssetDescriptor(
        id="sfx_pop_subtle_01",
        name="Pop Sutil",
        category="pop",
        relative_path="sfx/pops/pop_subtle_01.wav",
        duration_seconds=0.18,
        recommended_gain_db=-16.0,
        cooldown_frames=48.0,
        allowed_intents=("emphasis", "question"),
        prohibited_intents=(),
        author="DaVinci Flow",
        license="MIT / Libre de regalías",
        source="Generador procedural de DaVinci Flow",
    ),
    AssetDescriptor(
        id="sfx_bell_chime_01",
        name="Campana Reflexiva",
        category="bell",
        relative_path="sfx/bells/bell_chime_01.wav",
        duration_seconds=1.20,
        recommended_gain_db=-18.0,
        cooldown_frames=120.0,
        allowed_intents=("statement", "question"),
        prohibited_intents=("exclamation",),
        author="DaVinci Flow",
        license="MIT / Libre de regalías",
        source="Generador procedural de DaVinci Flow",
    ),
    AssetDescriptor(
        id="sfx_click_tech_01",
        name="Clic Tecnológico",
        category="click",
        relative_path="sfx/clicks/click_tech_01.wav",
        duration_seconds=0.08,
        recommended_gain_db=-15.0,
        cooldown_frames=36.0,
        allowed_intents=("emphasis", "statement"),
        prohibited_intents=(),
        author="DaVinci Flow",
        license="MIT / Libre de regalías",
        source="Generador procedural de DaVinci Flow",
    ),
)


class SFXCatalog:
    """Registro de catálogo para consultar y validar recursos de audio."""

    def __init__(self, assets: Sequence[AssetDescriptor] = DEFAULT_SFX_ASSETS) -> None:
        self._assets: dict[str, AssetDescriptor] = {a.id: a for a in assets}

    @property
    def total_assets(self) -> int:
        """Cantidad total de recursos registrados."""
        return len(self._assets)

    def get(self, asset_id: str) -> AssetDescriptor:
        """Obtiene un descriptor por su identificador único."""
        if asset_id not in self._assets:
            raise SFXCatalogError(f"Recurso SFX '{asset_id}' no encontrado en el catálogo.")
        return self._assets[asset_id]

    def list_by_category(self, category: str) -> tuple[AssetDescriptor, ...]:
        """Obtiene todos los descriptores que coinciden con una categoría."""
        cat_lower = category.strip().lower()
        return tuple(a for a in self._assets.values() if a.category.lower() == cat_lower)

    def list_all(self) -> tuple[AssetDescriptor, ...]:
        """Retorna todos los recursos del catálogo."""
        return tuple(self._assets.values())
