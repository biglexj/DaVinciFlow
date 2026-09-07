"""Preferencias no secretas de la ventana compartida."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from davinci_flow.ai.client import DEFAULT_MODEL
from davinci_flow.assets.library import CATEGORIES
from davinci_flow.editorial.model import EditorialError, EditorialOptions, Template

PREFERENCES_PATH = Path.home() / ".davinci_flow/editorial_preferences.json"


@dataclass
class Preferences:
    model: str = DEFAULT_MODEL
    mode: str = "highlights"
    format: str = "auto"
    density: str = "balanced"
    direction: str = ""
    paths: dict[str, str] = field(default_factory=dict)
    templates: list[dict] = field(default_factory=list)
    resource_ids: list[str] = field(default_factory=list)

    def validate(self):
        EditorialOptions(self.mode, self.format, self.density, self.direction).validate()
        if not isinstance(self.model, str) or not self.model.strip():
            raise EditorialError("Falta el modelo seleccionado.")
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
            result = cls(**json.loads(path.read_text(encoding='utf-8')))
            result.validate()
            return result
        except (ValueError, TypeError, KeyError) as error:
            raise EditorialError("No se pudieron leer las preferencias. Conserva el archivo para revisarlo.") from error
