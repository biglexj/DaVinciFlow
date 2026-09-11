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


def _traverse_folder_for_clips(folder: Any, current_path: str) -> list[MediaPoolPreset]:
    """Recorre recursivamente una carpeta del Media Pool buscando clips plantilla."""
    presets: list[MediaPoolPreset] = []
    if folder is None:
        return presets

    get_clips = getattr(folder, "GetClipList", None)
    if callable(get_clips):
        clips = get_clips() or []
        for clip in clips:
            get_property = getattr(clip, "GetClipProperty", None)
            clip_type = get_property("Type") if callable(get_property) else None
            if isinstance(clip_type, str) and clip_type.strip() and not any(
                word in clip_type.casefold() for word in ("fusion", "title", "título", "text", "texto")
            ):
                continue
            get_name = getattr(clip, "GetName", None)
            clip_name = str(get_name() or "").strip() if callable(get_name) else ""
            if not clip_name:
                clip_name = "Plantilla"
            bin_path = f"{current_path}/{clip_name}" if current_path else clip_name
            presets.append(
                MediaPoolPreset(
                    name=clip_name,
                    bin_path=bin_path,
                    media_item=clip,
                )
            )

    get_subfolders = getattr(folder, "GetSubFolderList", None)
    if callable(get_subfolders):
        subfolders = get_subfolders() or []
        for sub in subfolders:
            get_sub_name = getattr(sub, "GetName", None)
            sub_name = str(get_sub_name() or "").strip() if callable(get_sub_name) else "Subfolder"
            sub_path = f"{current_path}/{sub_name}" if current_path else sub_name
            presets.extend(_traverse_folder_for_clips(sub, sub_path))

    return presets


def scan_davinciflow_presets(media_pool: Any) -> tuple[MediaPoolPreset, ...]:
    """Escanea la bandeja 'DaVinciFlow', subcarpetas de títulos y presets en el Media Pool."""
    if media_pool is None:
        return ()

    get_root = getattr(media_pool, "GetRootFolder", None)
    if not callable(get_root):
        return ()

    root = get_root()
    if root is None:
        return ()

    get_subfolders = getattr(root, "GetSubFolderList", None)
    subfolders = get_subfolders() if callable(get_subfolders) else []
    subfolders = subfolders or []

    presets: list[MediaPoolPreset] = []
    seen_ids: set[Any] = set()

    def _add_preset(p: MediaPoolPreset) -> None:
        uid = getattr(p.media_item, "GetUniqueId", None)
        key = uid() if callable(uid) else id(p.media_item)
        if key not in seen_ids:
            seen_ids.add(key)
            presets.append(p)

    target_bin_names = {"davinciflow", "davinci flow", "davinci_flow"}

    # 1. Carpetas explícitas DaVinciFlow
    for folder in subfolders:
        get_name = getattr(folder, "GetName", None)
        folder_name = str(get_name() or "").strip() if callable(get_name) else ""
        if folder_name.lower() in target_bin_names:
            for p in _traverse_folder_for_clips(folder, folder_name):
                _add_preset(p)

    # 2. Carpetas de títulos o plantillas (Titles, Subtitles, Plantillas)
    title_bin_names = {"titles", "subtitles", "subtítulos", "títulos", "plantillas", "templates"}
    for folder in subfolders:
        get_name = getattr(folder, "GetName", None)
        folder_name = str(get_name() or "").strip() if callable(get_name) else ""
        if folder_name.lower() in title_bin_names:
            for p in _traverse_folder_for_clips(folder, folder_name):
                _add_preset(p)

    # 3. Clips colocados directamente en la raíz (Master)
    get_root_clips = getattr(root, "GetClipList", None)
    if callable(get_root_clips):
        get_root_name = getattr(root, "GetName", None)
        root_name = str(get_root_name() if callable(get_root_name) else "Master") or "Master"
        for clip in get_root_clips() or []:
            get_property = getattr(clip, "GetClipProperty", None)
            clip_type = get_property("Type") if callable(get_property) else None
            get_clip_name = getattr(clip, "GetName", None)
            clip_name = str(get_clip_name() if callable(get_clip_name) else "").strip()
            is_title = False
            if isinstance(clip_type, str) and any(w in clip_type.casefold() for w in ("fusion", "title", "título", "text", "texto")):
                is_title = True
            elif any(w in clip_name.casefold() for w in ("statement", "caption", "subtitle", "subtítulo", "plantilla")):
                is_title = True

            if is_title:
                _add_preset(
                    MediaPoolPreset(
                        name=clip_name or "Plantilla",
                        bin_path=f"{root_name}/{clip_name}" if root_name else clip_name,
                        media_item=clip,
                    )
                )

    return tuple(presets)


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
