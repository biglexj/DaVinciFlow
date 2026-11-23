# Únicamente llamadas de lectura al API de Resolve. Se ejecuta en su sandbox MCP.
def call(target, method, *args):
    try:
        if target is not None:
            return getattr(target, method)(*args)
    except Exception:
        return None


def items(kind, index):
    clips = timeline.GetItemListInTrack(kind, index) or []
    return clips.values() if isinstance(clips, dict) else clips


def text(item):
    comp = call(item, "GetFusionCompByIndex", 1)
    tools = call(comp, "GetToolList") or {}
    if isinstance(tools, dict):
        for tool in tools.values():
            if call(tool, "GetAttrs", "TOOLS_RegID") in ("TextPlus", "Fuse.TextPlus"):
                styled = call(tool, "GetInput", "StyledText")
                if styled and str(styled).strip():
                    return str(styled).strip()
    name = str(call(item, "GetName") or "").strip()
    if name:
        return name
    for key in ("Text", "Clip Name", "SubtitleText", "Subtitle", "Name"):
        value = str(call(item, "GetProperty", key) or "").strip()
        if value:
            return value
    return ""


def frame(item, method, field):
    for getter, args in ((method, (False,)), (method, ()), ("GetProperty", (field,))):
        try:
            return float(call(item, getter, *args))
        except (ValueError, TypeError):
            continue
    return None


def capture():
    if project is None:
        return {"ok": False, "message": "No hay un proyecto activo en DaVinci Resolve."}
    if timeline is None:
        return {"ok": False, "message": "El proyecto activo no tiene una línea de tiempo seleccionada."}
    count = int(timeline.GetTrackCount("subtitle") or 0)
    if not count:
        return {"ok": False, "message": "La línea de tiempo no contiene pistas de subtítulos."}
    if track > count:
        return {"ok": False, "message": f"La pista de subtítulos {track} no existe. Hay {count} pista(s)."}

    cues = []
    for item in items("subtitle", track):
        content = text(item)
        if content:
            cues.append({"text": content, "start_frame": frame(item, "GetStart", "Start"),
                         "end_frame": frame(item, "GetEnd", "End")})

    cuts = []
    flow_tracks = {
        "DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_BROLL", "DF_VISUAL_FX",
        "DF_SFX", "DF_SFX_TRANSITIONS", "DF_SFX_ACCENTS",
    }
    for kind in ("video", "audio"):
        for index in range(1, int(timeline.GetTrackCount(kind) or 0) + 1):
            if str(timeline.GetTrackName(kind, index) or "") in flow_tracks:
                continue
            for item in items(kind, index):
                media = call(item, "GetMediaPoolItem")
                cuts.append({
                    "kind": kind, "track": index, "id": str(item.GetUniqueId() or ""),
                    "start": float(item.GetStart()), "end": float(item.GetEnd()),
                    "left": item.GetLeftOffset(), "right": item.GetRightOffset(),
                    "type": str(call(item, "GetType") or "").strip().lower(),
                    "name": str(item.GetName() or ""), "media": media is not None,
                    "media_id": str(call(media, "GetUniqueId") or ""),
                })
    return {
        "ok": True,
        "snapshot": {
            "project": str(project.GetName()), "timeline": str(timeline.GetName()),
            "project_id": str(project.GetUniqueId() or ""), "timeline_id": str(timeline.GetUniqueId() or ""),
            "fps": timeline.GetSetting("timelineFrameRate"),
            "width": timeline.GetSetting("timelineResolutionWidth"),
            "height": timeline.GetSetting("timelineResolutionHeight"),
            "origin": timeline.GetStartFrame(), "cues": cues, "cut_records": cuts,
        },
    }


timeline = project.GetCurrentTimeline() if project is not None else None
result = capture()
