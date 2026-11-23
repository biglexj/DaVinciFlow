"""Importación explícita del audio de Voice Studio al proyecto activo de Resolve."""

from pathlib import Path

from davinci_flow.editorial.model import EditorialError
from davinci_flow.fetch.models import MediaKind
from davinci_flow.fetch.resolve_importer import ResolveMediaImporter

AUDIO_EXTENSIONS = ('wav', 'mp3', 'flac', 'm4a', 'aac', 'ogg', 'aiff', 'aif')
VOICE_BIN = 'DaVinci Flow · Voces'


def validate_voice_file(path: str | Path) -> Path:
    audio = Path(path).expanduser().resolve()
    if not audio.is_file() or audio.stat().st_size == 0:
        raise EditorialError('Selecciona un archivo de audio existente y con contenido.')
    if audio.suffix.casefold().lstrip('.') not in AUDIO_EXTENSIONS:
        raise EditorialError('El formato del archivo no es un audio compatible con esta importación.')
    return audio


def import_voice_file(path: str | Path) -> str:
    audio = validate_voice_file(path)
    success, detail = ResolveMediaImporter.import_to_resolve(audio, MediaKind.AUDIO, VOICE_BIN)
    if not success:
        raise EditorialError(f'El audio sigue guardado en disco, pero no se pudo importar: {detail}')
    return detail
