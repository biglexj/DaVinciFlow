"""Adaptador de importación y clasificación automática al Media Pool de DaVinci Resolve."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from davinci_flow.fetch.models import MediaKind

logger = logging.getLogger(__name__)


class ResolveImportError(Exception):
    """Fallo al conectar o importar elementos dentro de DaVinci Resolve."""


class ResolveMediaImporter:
    """Gestiona la inserción clasificada de archivos en carpetas del Media Pool."""

    @staticmethod
    def _find_subfolder(parent_folder: Any, name: str) -> Any | None:
        """Busca una subcarpeta por nombre exacto (case-insensitive) dentro de un Folder."""
        try:
            subfolders = parent_folder.GetSubFolderList() or []
            target_name = name.casefold()
            for sf in (subfolders.values() if isinstance(subfolders, dict) else subfolders):
                if sf.GetName().casefold() == target_name:
                    return sf
        except Exception as err:
            logger.debug("Error listando subcarpetas de %s: %s", parent_folder, err)
        return None

    @classmethod
    def get_or_create_bin(
        cls,
        media_pool: Any,
        parent_folder: Any,
        bin_name: str,
    ) -> Any:
        """Encuentra o crea un bin dentro del folder padre."""
        existing = cls._find_subfolder(parent_folder, bin_name)
        if existing is not None:
            return existing

        add_folder_fn = getattr(media_pool, "AddSubFolder", None)
        if callable(add_folder_fn):
            new_folder = add_folder_fn(parent_folder, bin_name)
            if new_folder is not None:
                return new_folder
        raise ResolveImportError(f'Resolve no pudo crear la carpeta {bin_name}.')

    @classmethod
    def resolve_target_folder(
        cls,
        media_pool: Any,
        kind: MediaKind,
        custom_bin_name: str | None = None,
    ) -> tuple[Any, str]:
        """Obtiene la carpeta de destino en el Media Pool según el tipo de medio.

        Sigue la jerarquía de Luna Fetch:
        - Luna Fetch / Videos
        - Luna Fetch / Música
        """
        root_folder = media_pool.GetRootFolder()
        if root_folder is None:
            raise ResolveImportError("No se pudo obtener la carpeta raíz (RootFolder) del Media Pool.")

        if custom_bin_name:
            folder = cls.get_or_create_bin(media_pool, root_folder, custom_bin_name)
            return folder, custom_bin_name

        # Contenedor raíz de Luna Fetch
        luna_root = cls.get_or_create_bin(media_pool, root_folder, "Luna Fetch")

        # Subcarpeta por tipo de medio (Música o Videos)
        category_name = "Videos" if kind == MediaKind.VIDEO else "Música"
        category_folder = cls.get_or_create_bin(media_pool, luna_root, category_name)

        return category_folder, f"Luna Fetch/{category_name}"

    @classmethod
    def import_to_resolve(
        cls,
        file_path: Path,
        kind: MediaKind = MediaKind.VIDEO,
        custom_bin_name: str | None = None,
        resolve_session: Any | None = None,
    ) -> tuple[bool, str]:
        """Importa un archivo local al Media Pool del proyecto activo en Resolve.

        Retorna (éxito, nombre_del_bin_o_error).
        """
        resolved_path = file_path.resolve()
        if not resolved_path.is_file():
            return False, f"El archivo a importar no existe: {resolved_path}"

        session = resolve_session
        if session is None:
            try:
                from davinci_flow.editorial.resolve_bridge import request
                result = request('import_media', file_path=str(resolved_path), kind=kind.value,
                                 custom_bin_name=custom_bin_name)
                return result['success'], result['bin_or_error']
            except Exception as err:
                return False, f"DaVinci Resolve no está accesible: {err}"

        project = session.project
        media_pool = project.GetMediaPool() if project else None
        if media_pool is None:
            return False, "No se pudo acceder al Media Pool del proyecto activo."

        try:
            previous_folder = media_pool.GetCurrentFolder()
            target_folder, bin_path_label = cls.resolve_target_folder(
                media_pool=media_pool,
                kind=kind,
                custom_bin_name=custom_bin_name,
            )

            # Establecer carpeta activa
            set_folder_fn = getattr(media_pool, "SetCurrentFolder", None)
            if not callable(set_folder_fn) or set_folder_fn(target_folder) is not True:
                raise ResolveImportError('Resolve no confirmó la carpeta de destino.')

            import_fn = getattr(media_pool, "ImportMedia", None)
            if not callable(import_fn):
                return False, "El Media Pool no soporta la función ImportMedia."

            imported = import_fn([str(resolved_path)])
            if not imported:
                return False, f"Resolve no pudo importar el archivo {resolved_path.name}."

            return True, bin_path_label

        except Exception as err:
            return False, f"Fallo al insertar en el Media Pool: {err}"
        finally:
            if 'previous_folder' in locals() and previous_folder is not None:
                media_pool.SetCurrentFolder(previous_folder)
