"""Adaptador estricto de plantillas sobre los registros y reversión existentes."""

import hashlib
from pathlib import Path
from typing import Any

from davinci_flow.editorial.model import EditorialError, Proposal
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.editorial.template_files import ROOT_TOOL, prepare_comp, template_bytes


def text_tool(comp: Any, tool_name: str = "") -> Any:
    if comp is None or comp is False:
        raise EditorialError("El clip no contiene una composición Fusion accesible.")
    if tool_name:
        tool = comp.FindTool(tool_name)
        candidates = [tool] if tool is not None else []
    else:
        tools = comp.GetToolList(False) or {}
        values = tools.values() if isinstance(tools, dict) else tools
        candidates = []
        for tool in values:
            attrs = tool.GetAttrs()
            if isinstance(attrs, dict) and attrs.get("TOOLS_RegID") in ("TextPlus", "Text3D", "Fuse.TextPlus"):
                candidates.append(tool)
    if len(candidates) != 1:
        raise EditorialError("Plantilla ambigua: indica el nombre del nodo de texto en el catálogo.")
    return candidates[0]


def set_template_text(comp: Any, text: str, tool_name: str = "", input_id: str = "StyledText") -> None:
    tool = text_tool(comp, tool_name)
    # Nunca sustituir toda la composición ni sus nodos para editar un texto.
    if tool.SetInput(input_id, text) is False or tool.GetInput(input_id) != text:
        raise EditorialError("La plantilla no confirmó el texto solicitado.")


def connect_template_output(comp: Any, template: Any) -> None:
    """Resolve puede importar la macro sin enlazar una referencia adelantada a su salida."""
    target = comp.FindTool("DF_EditorialOutput")
    if target is None:
        return  # La composición ya incluía su propia salida.
    root = ROOT_TOOL.search(template_bytes(template).decode("utf-8-sig"))
    source = comp.FindTool(root[1]) if root else None
    outputs = source.GetOutputList() if source is not None else {}
    images = [o for o in (outputs or {}).values() if o.GetAttrs().get("OUTS_DataType") == "Image"]
    if len(images) != 1 or target.ConnectInput("Input", images[0]) is False:
        raise EditorialError("La plantilla no confirmó una salida de imagen única.")
    inputs = target.GetInputList() or {}
    connected = [i for i in inputs.values() if i.GetAttrs().get("INPS_ID") == "Input"
                 and i.GetConnectedOutput() is not None]
    if len(connected) != 1:
        raise EditorialError("Resolve dejó la salida del título desconectada.")


class EditorialWriter(ResolveTimelineWriter):
    def __init__(self, timeline: Any, media_pool: Any, proposal: Proposal,
                 handles: dict[str, Any], **kwargs: Any) -> None:
        kwargs.setdefault("temp_root", Path.home() / ".davinci_flow/generated")
        super().__init__(timeline, media_pool, **kwargs)
        self.proposal = proposal
        self.templates = {t.id: t for t in proposal.templates}
        self.handles = handles
        plan = proposal.generation_plan()
        self.assignments = {
            self._native_name("exec_" + plan.plan_id, f"item_{plan.plan_id}_b{i}_{role[:3]}"): self.templates[tid]
            for i, d in enumerate(proposal.decisions, 1) if d.enabled
            for role, tid in d.templates.items()
        }
        self.expected_text = {
            self._native_name("exec_" + plan.plan_id, f"item_{plan.plan_id}_b{i}_{role[:3]}"): getattr(d, role)
            for i, d in enumerate(proposal.decisions, 1) if d.enabled
            for role in d.templates
        }
        self.track_manager.ensure_dedicated_tracks = self.ensure_text_tracks

    def ensure_text_tracks(self) -> dict[str, int]:
        """Crea solo tres pistas de texto; nunca renombra una pista existente ajena."""
        names = ("DF_CONTEXT", "DF_MAIN", "DF_ACCENT")
        count = int(self.timeline.GetTrackCount("video"))
        mapping = {}
        highest_other = 0
        for index in range(1, count + 1):
            name = str(self.timeline.GetTrackName("video", index))
            if name in names:
                if name in mapping:
                    raise EditorialError(f"Hay dos pistas llamadas {name}; resuelve la ambigüedad.")
                mapping[name] = index
                locked = self.timeline.GetIsTrackLocked("video", index)
                if locked:
                    raise EditorialError(f"Desbloquea {name} antes de aplicar.")
            else:
                highest_other = index
        if mapping and min(mapping.values()) <= highest_other:
            raise EditorialError("Coloca las pistas de texto por encima del montaje antes de aplicar.")
        for name in names:
            if name in mapping:
                continue
            if self.timeline.AddTrack("video") is not True:
                raise EditorialError("Resolve rechazó una pista de texto.")
            count += 1
            if int(self.timeline.GetTrackCount("video")) != count:
                raise EditorialError("Resolve no confirmó la nueva pista.")
            if self.timeline.SetTrackName("video", count, name) is not True:
                raise EditorialError("Resolve rechazó el nombre de la pista.")
            if self.timeline.GetTrackName("video", count) != name:
                raise EditorialError("Resolve no confirmó el nombre de la pista.")
            mapping[name] = count
        return mapping

    def preflight(self) -> None:
        for template in self.assignments.values():
            if template.source == "media_pool":
                if template.id not in self.handles:
                    raise EditorialError(f"Ya no existe la plantilla {template.name} en DaVinci Flow.")
            else:
                if hashlib.sha256(template_bytes(template)).hexdigest() != template.fingerprint:
                    raise EditorialError(f"La plantilla {template.name} cambió o desapareció. Vuelve a analizar.")
        names = {"context": "DF_CONTEXT", "main": "DF_MAIN", "accent": "DF_ACCENT"}
        for track in range(1, int(self.timeline.GetTrackCount("video")) + 1):
            track_name = self.timeline.GetTrackName("video", track)
            if track_name not in names.values():
                continue
            role = next(r for r, n in names.items() if n == track_name)
            for item in self._iter_values(self.timeline.GetItemListInTrack("video", track)):
                for cue, decision in zip(self.proposal.snapshot.cues, self.proposal.decisions):
                    if decision.enabled and role in decision.templates and item.GetStart() < cue.end_frame and item.GetEnd() > cue.start_frame:
                        if item.GetName() not in self.assignments:
                            raise EditorialError("Hay un clip ajeno en el intervalo de una pista de texto. Desplázalo o usa otra secuencia.")

    def _find_timeline_item(self, track_type: str, track_index: int, expected_name: str) -> Any:
        matches = [item for item in self._iter_values(self.timeline.GetItemListInTrack(track_type, track_index))
                   if item.GetName() == expected_name]
        if len(matches) > 1:
            raise EditorialError("Hay clips generados duplicados; revisa la muestra antes de reaplicar.")
        if not matches:
            return None
        item = matches[0]
        template = self.assignments[expected_name]
        tool = text_tool(item.GetFusionCompByIndex(1), template.text_tool)
        if tool.GetInput(template.text_input) != self.expected_text[expected_name]:
            raise EditorialError("El texto generado se editó en Resolve. No se sobrescribirá automáticamente.")
        return item

    def _resolve_record_frame(self, frame: float) -> int:
        # Los subtítulos nativos tienen tiempos absolutos; no inferir el origen por magnitud.
        return int(round(frame))

    def _append_media_item(self, media_item: Any, media_type: int, track_type: str,
                           track_index: int, record_frame: int, duration_frames: float) -> Any:
        duration = int(round(duration_frames))
        result = self.media_pool.AppendToTimeline([{
            "mediaPoolItem": media_item, "mediaType": media_type, "trackIndex": track_index,
            # Resolve 21.0.0b.33 comprobado: endFrame=46 produce duración 46, no 47.
            "recordFrame": record_frame, "startFrame": 0, "endFrame": duration,
        }])
        items = list(self._iter_values(result))
        if len(items) != 1:
            if items:
                self._delete_items(items, require_success=True)
            raise EditorialError("Resolve no devolvió exactamente un clip.")
        try:
            self._verify_native_item(items[0], track_type, track_index, record_frame, duration)
            return items[0]
        except Exception:
            self._delete_items(items, require_success=True)
            raise

    def _verify_native_item(self, item: Any, track_type: str, track_index: int,
                            record_frame: int, duration_frames: float) -> None:
        track = item.GetTrackTypeAndIndex()
        if not isinstance(track, (list, tuple)) or list(track) != [track_type, track_index]:
            raise EditorialError("Resolve no confirmó la pista de destino.")
        for value, expected in ((item.GetStart(), record_frame), (item.GetDuration(), round(duration_frames))):
            if not isinstance(value, (int, float)) or abs(value - expected) > 0.01:
                raise EditorialError("Resolve no confirmó posición y duración exactas.")

    def _insert_fusion_title(self, **kwargs: Any) -> Any:
        template = self.assignments[kwargs["native_name"]]
        duration = int(round(kwargs["end_frame"] - kwargs["start_frame"]))
        media = (self.handles[template.id] if template.source == "media_pool"
                 else self._get_carrier_media_item(self._plan_carrier_frames, fps=kwargs["fps"]))
        item = self._append_media_item(media, 1, "video", kwargs["track_index"],
                                       int(round(kwargs["start_frame"])), duration)
        try:
            if template.source != "media_pool":
                comp_path = prepare_comp(template, self.temp_root / "editorial_templates")
                if not item.ImportFusionComp(str(comp_path)):
                    raise EditorialError(f"Resolve no pudo importar {template.name}; prepara una composición en el Media Pool.")
            comp = item.GetFusionCompByIndex(1)
            if template.source != "media_pool":
                connect_template_output(comp, template)
            set_template_text(comp, kwargs["text"], template.text_tool, template.text_input)
            if comp.SetAttrs({"COMPN_GlobalStart": 0, "COMPN_GlobalEnd": duration - 1,
                              "COMPN_RenderStart": 0, "COMPN_RenderEnd": duration - 1}) is False:
                raise EditorialError("La composición rechazó el rango de animación.")
            self._set_native_name(item, kwargs["native_name"])
            if item.GetName() != kwargs["native_name"]:
                raise EditorialError("Resolve no confirmó la identidad del clip generado.")
            return item
        except Exception:
            self._delete_items([item], require_success=True)
            raise
