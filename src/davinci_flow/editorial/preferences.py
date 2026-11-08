"""Preferencias no secretas de la ventana compartida."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from davinci_flow.ai.client import DEFAULT_MODEL
from davinci_flow.ai.providers.base import (
    GEMINI_PROVIDER,
    MINIMAX_MODELS,
    MINIMAX_PROVIDER,
    provider_names,
)
from davinci_flow.assets.library import CATEGORIES
from davinci_flow.editorial.model import EditorialError, EditorialOptions, Template

PREFERENCES_PATH = Path.home() / ".davinci_flow/editorial_preferences.json"


@dataclass
class Preferences:
    model: str = DEFAULT_MODEL
    provider: str = GEMINI_PROVIDER
    mode: str = "highlights"
    format: str = "auto"
    density: str = "balanced"
    direction: str = ""
    paths: dict[str, str] = field(default_factory=dict)
    templates: list[dict] = field(default_factory=list)
    resource_ids: list[str] = field(default_factory=list)
    track_mode: str = "triple"
    batch_size: str = "20"
    long_context_enabled: bool = False

    def validate(self):
        EditorialOptions(self.mode, self.format, self.density, self.direction, track_mode=self.track_mode).validate()
        if not isinstance(self.model, str) or not self.model.strip():
            raise EditorialError("Falta el modelo seleccionado.")
        if self.provider not in provider_names():
            raise EditorialError(
                f"Proveedor de IA desconocido: '{self.provider}'. "
                f"Opciones válidas: {', '.join(provider_names())}."
            )
        if self.batch_size not in ("20", "50", "100", "500", "all"):
            raise EditorialError("El tamaño de tanda debe ser 20, 50, 100, 500 o todos los subtítulos.")
        if type(self.long_context_enabled) is not bool:
            raise EditorialError("La opción de modelos de contexto largo debe ser booleana.")
        if not isinstance(self.paths, dict) or any(k not in CATEGORIES or not isinstance(v, str) for k, v in self.paths.items()):
            raise EditorialError("Rutas de biblioteca inválidas.")
        if not isinstance(self.resource_ids, list) or len(self.resource_ids) > 80 or not all(isinstance(i, str) for i in self.resource_ids):
            raise EditorialError("Selección de recursos inválida.")
        for template in self.templates:
            Template(**template)

    def save(self, path: Path = PREFERENCES_PATH):
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path = PREFERENCES_PATH):
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                data.setdefault("track_mode", "triple")
                data.setdefault("batch_size", "20")
                data.setdefault("long_context_enabled", False)
                provider = str(data.get("provider") or GEMINI_PROVIDER).strip().lower()
                data["provider"] = provider
                model = str(data.get("model") or "").strip()
                if provider == MINIMAX_PROVIDER and model not in MINIMAX_MODELS:
                    # El modelo guardado pertenece a otro proveedor: se restituye el de Minimax.
                    data["model"] = MINIMAX_MODELS[0]
            result = cls(**data)
            result.validate()
            return result
        except (ValueError, TypeError, KeyError) as error:
            raise EditorialError("No se pudieron leer las preferencias. Conserva el archivo para revisarlo.") from error

