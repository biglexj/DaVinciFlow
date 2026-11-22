"""Vistas previas originales de los títulos: nunca se inventa su aspecto."""

from davinci_flow.user_data import user_data_dir
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile

from davinci_flow.editorial.model import EditorialError, Template

VIDEO_SUFFIXES = (".mp4", ".webm", ".mov")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif")
MAX_PREVIEW_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class TitlePreview:
    image: Path | None = None
    video: Path | None = None


def captured_preview_path(template: Template) -> Path:
    key = hashlib.sha256(f'{template.id}:{template.locator}:{template.fingerprint}:640x360-v1'.encode()).hexdigest()
    return user_data_dir() / 'cache/title_captures' / (key + '.png')


@lru_cache(maxsize=32)
def _archive_names(path: str, modified: int, size: int) -> frozenset[str]:
    with ZipFile(path) as archive:
        return frozenset(archive.namelist())


def title_preview_kind(template: Template) -> str | None:
    """Comprueba las muestras sin extraerlas ni escribir en la caché."""
    if template.source in {'media_pool', 'native'}:
        return 'image' if captured_preview_path(template).is_file() else None
    try:
        if template.source == 'installed_archive':
            path, member = template.locator.split('::', 1)
            stat = Path(path).stat()
            names = _archive_names(path, stat.st_mtime_ns, stat.st_size)
            stem = str(PurePosixPath(member).with_suffix(''))
            def exists(suffix):
                return stem + suffix in names or stem + '.large' + suffix in names
        else:
            def exists(suffix):
                return Path(template.locator).with_suffix(suffix).is_file()
        if any(exists(s) for s in VIDEO_SUFFIXES):
            return 'video'
        if any(exists(s) for s in IMAGE_SUFFIXES):
            return 'image'
    except (OSError, BadZipFile, ValueError):
        return None
    return 'image' if captured_preview_path(template).is_file() else None


def read_title_preview(template: Template, cache_dir: Path | None = None) -> TitlePreview:
    """Usa solo recursos con el mismo nombre y carpeta que la plantilla."""
    if template.source in {"media_pool", "native"}:
        capture = captured_preview_path(template)
        return TitlePreview(image=capture if capture.is_file() else None)
    try:
        if template.source != "installed_archive":
            source = Path(template.locator)
            image = next((source.with_suffix(s) for s in IMAGE_SUFFIXES
                          if source.with_suffix(s).is_file()), None)
            video = next((source.with_suffix(s) for s in VIDEO_SUFFIXES
                          if source.with_suffix(s).is_file()), None)
            capture = captured_preview_path(template)
            return TitlePreview(image or (capture if capture.is_file() else None), video)
        path, member = template.locator.split("::", 1)
        stat = Path(path).stat()
        names = _archive_names(path, stat.st_mtime_ns, stat.st_size)
        stem = str(PurePosixPath(member).with_suffix(""))
        cache = cache_dir or user_data_dir() / "cache/title_previews"

        def extract(suffixes: tuple[str, ...]) -> Path | None:
            candidates = [stem + s for s in suffixes]
            candidates += [stem + ".large" + s for s in suffixes]
            chosen = next((c for c in candidates if c in names), None)
            if chosen is None:
                return None
            key = hashlib.sha256(f"{path}:{stat.st_mtime_ns}:{stat.st_size}:{chosen}".encode()).hexdigest()
            destination = cache / (key + PurePosixPath(chosen).suffix)
            if destination.is_file():
                return destination
            with ZipFile(path) as archive:
                if archive.getinfo(chosen).file_size > MAX_PREVIEW_BYTES:
                    raise EditorialError("La vista previa supera el tamaño permitido.")
                content = archive.read(chosen)
            cache.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            return destination

        capture = captured_preview_path(template)
        return TitlePreview(extract(IMAGE_SUFFIXES) or (capture if capture.is_file() else None), extract(VIDEO_SUFFIXES))
    except (OSError, BadZipFile, KeyError, ValueError) as error:
        raise EditorialError(f"No se pudo leer la vista previa de {template.name}.") from error
