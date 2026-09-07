"""Biblioteca por rutas: inventario local ligero, sin decodificar vídeo ni audio."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from davinci_flow.assets.broll_catalog import SUPPORTED_VIDEO_EXTENSIONS, SUPPORTED_AUDIO_EXTENSIONS

CATEGORIES = {
    "visuals": "Visuals y B-rolls",
    "sfx": "Efectos de sonido",
    "music": "Música",
    "titles": "Títulos y Fusion",
    "documents": "Textos y documentos",
}
EXTENSIONS = {
    "visuals": SUPPORTED_VIDEO_EXTENSIONS | {".jpg", ".jpeg", ".png", ".webp"},
    "sfx": SUPPORTED_AUDIO_EXTENSIONS,
    "music": SUPPORTED_AUDIO_EXTENSIONS,
    "titles": {".setting", ".comp", ".drfx"},
    "documents": {".txt", ".md", ".srt", ".pdf", ".docx"},
}


@dataclass(frozen=True)
class Resource:
    id: str
    category: str
    name: str
    path: str

    def context(self) -> dict[str, str]:
        return {"id": self.id, "category": self.category, "name": self.name[:250]}


def scan_library(paths: dict[str, str], limit: int = 2000) -> tuple[tuple[Resource, ...], tuple[str, ...]]:
    resources, diagnostics = [], []
    for category in CATEGORIES:
        value = paths.get(category, "").strip()
        if not value:
            continue
        root = Path(value).expanduser()
        if not root.is_dir():
            diagnostics.append(f"{CATEGORIES[category]}: la carpeta no existe.")
            continue
        count = 0
        def onerror(error):
            diagnostics.append(f"{CATEGORIES[category]}: no se pudo leer una subcarpeta ({error.strerror}).")
        for directory, folders, files in os.walk(root, followlinks=False, onerror=onerror):
            folders[:] = sorted(f for f in folders if not f.startswith('.') and not Path(directory, f).is_symlink())
            for name in sorted(files):
                path = Path(directory, name)
                if path.suffix.lower() not in EXTENSIONS[category] or path.is_symlink():
                    continue
                count += 1
                if count > limit:
                    break
                identity = category + ':' + str(path.resolve()).casefold()
                resources.append(Resource(hashlib.sha256(identity.encode()).hexdigest()[:24], category,
                                          path.relative_to(root).as_posix(), str(path.resolve())))
            if count > limit:
                diagnostics.append(f"{CATEGORIES[category]}: inventario limitado a {limit} archivos; elige una carpeta más concreta.")
                break
    return tuple(resources), tuple(diagnostics)
