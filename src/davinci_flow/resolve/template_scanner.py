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
    """Escanea la bandeja 'DaVinciFlow' (o 'DaVinci Flow') en el Media Pool y retorna todos los presets encontrados."""
    if media_pool is None:
        return ()

    get_root = getattr(media_pool, "GetRootFolder", None)
    if not callable(get_root):
        return ()

    root = get_root()
    if root is None:
        return ()

    get_subfolders = getattr(root, "GetSubFolderList", None)
    if not callable(get_subfolders):
        return ()

    subfolders = get_subfolders() or []
    presets: list[MediaPoolPreset] = []

    target_bin_names = {"davinciflow", "davinci flow", "davinci_flow"}

    for folder in subfolders:
        get_name = getattr(folder, "GetName", None)
        folder_name = str(get_name() or "").strip() if callable(get_name) else ""
        if folder_name.lower() in target_bin_names:
            # Encontrada la carpeta principal DaVinciFlow
            # 1. Clips directamente en DaVinciFlow
            presets.extend(_traverse_folder_for_clips(folder, folder_name))

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
