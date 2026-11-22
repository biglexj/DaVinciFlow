"""Escaneo y descubrimiento de plantillas y presets Fusion/Text+ dentro de la bandeja DaVinciFlow del Media Pool."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaPoolPreset:
    """Representa una plantilla o preset de Text+/Fusion almacenado en el Media Pool."""

    name: str
    bin_path: str
    media_item: Any

    @property
    def display_label(self) -> str:
        """Etiqueta legible para mostrar en selectores de la interfaz."""
        return f"📁 {self.bin_path}"


TITLE_WORDS = ('fusion', 'title', 'título', 'text', 'texto')
TEMPLATE_FOLDERS = {'davinciflow', 'davinci flow', 'davinci_flow', 'titles', 'subtitles',
                    'subtítulos', 'títulos', 'plantillas', 'templates'}


def _values(items):
    return items.values() if isinstance(items, dict) else items or ()


def _traverse_folder_for_clips(folder: Any, current_path: str,
                               allow_untyped: bool = False) -> list[MediaPoolPreset]:
    if folder is None:
        return []
    folder_name = str(getattr(folder, 'GetName', lambda: '')() or '').strip()
    allow_untyped = allow_untyped or folder_name.casefold() in TEMPLATE_FOLDERS
    presets = []
    for clip in _values(getattr(folder, 'GetClipList', lambda: [])()):
        kind = getattr(clip, 'GetClipProperty', lambda key: None)('Type')
        name = str(getattr(clip, 'GetName', lambda: '')() or '').strip()
        if isinstance(kind, str) and kind.strip():
            kind_cf = kind.casefold()
            if 'subtitle' in kind_cf or 'subtítulo' in kind_cf:
                continue
            if not any(word in kind_cf for word in TITLE_WORDS):
                continue
        elif not allow_untyped and not any(word in name.casefold() for word in
                                          ('statement', 'caption', 'subtitle', 'subtítulo', 'plantilla')):
            continue
        name = name or 'Plantilla'
        presets.append(MediaPoolPreset(name, f'{current_path}/{name}', clip))
    for child in _values(getattr(folder, 'GetSubFolderList', lambda: [])()):
        name = str(getattr(child, 'GetName', lambda: 'Subfolder')() or 'Subfolder')
        presets.extend(_traverse_folder_for_clips(child, f'{current_path}/{name}', allow_untyped))
    return presets


def scan_davinciflow_presets(media_pool: Any) -> tuple[MediaPoolPreset, ...]:
    """Lee títulos en cualquier carpeta sin depender de su nombre o ubicación."""
    if media_pool is None:
        return ()
    root = getattr(media_pool, 'GetRootFolder', lambda: None)()
    if root is None:
        return ()
    name = str(getattr(root, 'GetName', lambda: 'Master')() or 'Master')
    # Conservar los localizadores históricos de las carpetas de primer nivel.
    found = _traverse_folder_for_clips(root, name)
    result, seen = [], set()
    for preset in found:
        uid = getattr(preset.media_item, 'GetUniqueId', lambda: None)()
        key = uid or id(preset.media_item)
        if key in seen:
            continue
        seen.add(key)
        path = preset.bin_path
        if path.startswith(name + '/') and path.count('/') >= 2:
            path = path[len(name) + 1:]
        result.append(MediaPoolPreset(preset.name, path, preset.media_item))
    return tuple(result)


def ensure_davinciflow_bin(media_pool: Any) -> Any:
    """Verifica que exista la bandeja 'DaVinciFlow' en el Media Pool o la crea si es posible."""
    if media_pool is None:
        return None

    get_root = getattr(media_pool, "GetRootFolder", None)
    if not callable(get_root):
        return None

    root = get_root()
    if root is None:
        return None

    get_subfolders = getattr(root, "GetSubFolderList", None)
    if callable(get_subfolders):
        for folder in get_subfolders() or []:
            get_name = getattr(folder, "GetName", None)
            name = str(get_name() or "").strip() if callable(get_name) else ""
            if name.lower() in ("davinciflow", "davinci flow", "davinci_flow"):
                return folder

    # Intentar crear la subcarpeta DaVinciFlow en el Media Pool
    add_sub = getattr(media_pool, "AddSubFolder", None)
    if callable(add_sub):
        try:
            return add_sub(root, "DaVinciFlow")
        except Exception:
            pass

    folder_add_sub = getattr(root, "AddSubFolder", None)
    if callable(folder_add_sub):
        try:
            return folder_add_sub("DaVinciFlow")
        except Exception:
            pass

    return None
