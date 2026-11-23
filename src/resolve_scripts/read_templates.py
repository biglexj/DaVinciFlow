# Lectura del inventario. El filtrado de títulos y la identidad se resuelven en Rust.
def entries(value):
    return value.values() if isinstance(value, dict) else (value or [])


def inventory():
    if project is None:
        return {"ok": False}
    pool = project.GetMediaPool()
    root = pool.GetRootFolder() if pool is not None else None
    rows = []
    stack = [(root, [])] if root is not None else []
    while stack:
        folder, parents = stack.pop()
        parts = parents + [str(folder.GetName() or "")]
        for clip in entries(folder.GetClipList()):
            rows.append({
                "id": str(clip.GetUniqueId() or ""),
                "type": clip.GetClipProperty("Type"),
                "name": str(clip.GetName() or ""),
                "folders": parts,
            })
        children = list(entries(folder.GetSubFolderList()))
        stack.extend((child, parts) for child in reversed(children))
    return {"ok": True, "clips": rows}


result = inventory()
