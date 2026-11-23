# Adaptación de la operación explícita de importar un medio al Media Pool.
def import_media():
    if project is None:
        return {"success": False, "message": "No hay un proyecto activo en DaVinci Resolve."}
    pool = project.GetMediaPool()
    folder = pool.GetRootFolder() if pool is not None else None
    if folder is None:
        return {"success": False, "message": "No se pudo acceder al Media Pool del proyecto."}
    previous = pool.GetCurrentFolder()
    try:
        for name in folders:
            children = folder.GetSubFolderList() or []
            if isinstance(children, dict):
                children = children.values()
            match = next((item for item in children if str(item.GetName()).casefold() == name.casefold()), None)
            folder = match if match is not None else pool.AddSubFolder(folder, name)
            if folder is None:
                return {"success": False, "message": "Resolve no pudo preparar la carpeta de destino."}
        if pool.SetCurrentFolder(folder) is not True:
            return {"success": False, "message": "Resolve no confirmó la carpeta de destino."}
        if not pool.ImportMedia([file_path]):
            return {"success": False, "message": "Resolve no confirmó la importación del archivo."}
        return {"success": True, "bin": "/".join(folders)}
    finally:
        if previous is not None:
            pool.SetCurrentFolder(previous)


result = import_media()
