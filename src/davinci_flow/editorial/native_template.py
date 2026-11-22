"""Importación de títulos DRB sin modificar los archivos o clips originales."""

from typing import Any

from davinci_flow.editorial.model import EditorialError, Template


def _values(values):
    return values.values() if isinstance(values, dict) else values or ()


def _clips(folder):
    result = list(_values(folder.GetClipList()))
    for child in _values(folder.GetSubFolderList()):
        result.extend(_clips(child))
    return result


def import_native_template(media_pool: Any, template: Template) -> Any:
    """Una carpeta por contenido evita duplicar la plantilla entre aplicaciones."""
    root = media_pool.GetRootFolder()
    name = 'DF_Preset_' + template.fingerprint[:20]
    folder = next((f for f in _values(root.GetSubFolderList()) if f.GetName() == name), None)
    if folder is None:
        folder = media_pool.AddSubFolder(root, name)
    if folder is None or folder is False:
        raise EditorialError('Resolve no pudo preparar la carpeta de la plantilla.')
    clips = _clips(folder)
    if not clips:
        previous = media_pool.GetCurrentFolder()
        try:
            if media_pool.SetCurrentFolder(folder) is not True:
                raise EditorialError('Resolve no confirmó la carpeta de la plantilla.')
            if media_pool.ImportFolderFromFile(template.locator) is not True:
                raise EditorialError(f'Resolve no pudo importar {template.name}.')
            clips = _clips(folder)
        finally:
            if previous is not None:
                if media_pool.SetCurrentFolder(previous) is not True:
                    raise EditorialError('Resolve no pudo restaurar la carpeta del Media Pool.')
    if len(clips) != 1:
        raise EditorialError('El DRB debe contener un único título. Prepara una plantilla por archivo.')
    return clips[0]
