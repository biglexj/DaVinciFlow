from dataclasses import replace
import hashlib
from pathlib import Path
from typing import Any

from davinci_flow.editorial.model import EditorialConflictDetail, EditorialConflictError, EditorialError, Proposal
from davinci_flow.editorial.sources import basic_titles
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.themes.tokens import ThemeTokens
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
        if not candidates:
            tools_rec = comp.GetToolList(True) or {}
            values_rec = tools_rec.values() if isinstance(tools_rec, dict) else tools_rec
            for tool in values_rec:
                attrs = tool.GetAttrs()
                if isinstance(attrs, dict) and attrs.get("TOOLS_RegID") in ("TextPlus", "Text3D", "Fuse.TextPlus"):
                    candidates.append(tool)
    if not candidates:
        raise EditorialError("Plantilla ambigua: indica el nombre del nodo de texto en el catálogo.")
    if len(candidates) > 1:
        preferred = [
            t for t in candidates
            if isinstance(getattr(t, "Name", None), str)
            and any(n in t.Name.lower() for n in ("template", "styled", "main", "principal"))
        ]
        if len(preferred) == 1:
            return preferred[0]
        raise EditorialError("Plantilla ambigua: indica el nombre del nodo de texto en el catálogo.")
    return candidates[0]


def calculate_layer_y(role: str, active_roles: tuple[str, ...], is_vertical: bool) -> float:
    """Calcula la coordenada Center Y para ubicar subtítulos en el tercio inferior seguro."""
    if is_vertical:
        # Formato vertical 9:16 (Shorts, TikTok, Reels): tercio inferior compacto (Y ~ 0.285 a 0.355)
        if len(active_roles) >= 3:
            positions = {"context": 0.355, "main": 0.320, "accent": 0.285}
        elif len(active_roles) == 2:
            if "context" in active_roles and "main" in active_roles:
                positions = {"context": 0.355, "main": 0.320}
            elif "main" in active_roles and "accent" in active_roles:
                positions = {"main": 0.325, "accent": 0.290}
            else:
                positions = {"context": 0.355, "accent": 0.320}
        else:
            positions = {role: 0.315}
    else:
        # Formato horizontal 16:9: tercio inferior estándar
        if len(active_roles) >= 3:
            positions = {"context": 0.240, "main": 0.190, "accent": 0.140}
        elif len(active_roles) == 2:
            if "context" in active_roles and "main" in active_roles:
                positions = {"context": 0.240, "main": 0.190}
            elif "main" in active_roles and "accent" in active_roles:
                positions = {"main": 0.200, "accent": 0.150}
            else:
                positions = {"context": 0.240, "accent": 0.190}
        else:
            positions = {role: 0.180}
    return positions.get(role, 0.320 if is_vertical else 0.190)


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
        fresh_basic = {t.id: t for t in basic_titles()}
        synced_templates = tuple(fresh_basic.get(t.id, t) for t in proposal.templates)
        if synced_templates != proposal.templates:
            proposal = replace(proposal, templates=synced_templates)
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
        is_vertical = proposal.snapshot.height > proposal.snapshot.width
        self.target_y_by_native_name = {
            self._native_name("exec_" + plan.plan_id, f"item_{plan.plan_id}_b{i}_{role[:3]}"): calculate_layer_y(
                role,
                tuple(r for r in ("context", "main", "accent") if getattr(d, r).strip()),
                is_vertical,
            )
            for i, d in enumerate(proposal.decisions, 1) if d.enabled
            for role in d.templates
        }
        self.track_manager.ensure_dedicated_tracks = self.ensure_tracks

    def ensure_tracks(self) -> dict[str, int]:
        mapping = self.ensure_text_tracks()
        plan = self.proposal.generation_plan()
        has_sfx = any(bool(b.sfx_proposal) for b in plan.blocks if b.is_enabled)
        if has_sfx:
            count = int(self.timeline.GetTrackCount("audio"))
            sfx_index = None
            for index in range(1, count + 1):
                name = str(self.timeline.GetTrackName("audio", index))
                if name == "DF_SFX":
                    sfx_index = index
                    break
            if sfx_index is None:
                if self.timeline.AddTrack("audio") is True:
                    count += 1
                    self.timeline.SetTrackName("audio", count, "DF_SFX")
                    sfx_index = count
                else:
                    sfx_index = 1
            mapping["DF_SFX"] = sfx_index
        return mapping

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

    def clean_previous_df_clips(self) -> int:
        """Elimina clips de DaVinci Flow (prefijo DF_) en pistas exclusivas que solapen con el bloque activo para admitir iteraciones sucesivas sin alterar otros bloques."""
        if not self.proposal.snapshot.cues:
            return 0
        block_start = float(self.proposal.snapshot.cues[0].start_frame)
        block_end = float(self.proposal.snapshot.cues[-1].end_frame)

        names = {"DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_SFX"}
        deleted_count = 0
        for track_type in ("video", "audio"):
            count = int(self.timeline.GetTrackCount(track_type) or 0)
            for idx in range(1, count + 1):
                name = str(self.timeline.GetTrackName(track_type, idx) or "")
                if name in names:
                    items = self.timeline.GetItemListInTrack(track_type, idx) or []
                    if isinstance(items, dict):
                        items = list(items.values())
                    df_items = []
                    for it in items:
                        it_name = str(getattr(it, "GetName", lambda: "")() or "")
                        if it_name.startswith("DF_") or it_name.startswith("DF__"):
                            try:
                                it_start = float(it.GetStart())
                                it_end = float(it.GetEnd())
                                if it_start < block_end and it_end > block_start:
                                    df_items.append(it)
                            except (TypeError, ValueError, AttributeError):
                                df_items.append(it)
                    if df_items:
                        self.timeline.DeleteClips(df_items, False)
                        deleted_count += len(df_items)
        return deleted_count

    def preflight(self) -> None:
        for template in self.assignments.values():
            if template.source == "media_pool":
                if template.id not in self.handles:
                    raise EditorialError(f"Ya no existe la plantilla {template.name} en DaVinci Flow.")
            else:
                if hashlib.sha256(template_bytes(template)).hexdigest() != template.fingerprint:
                    raise EditorialError(f"La plantilla {template.name} cambió o desapareció. Vuelve a analizar.")
        names = {"context": "DF_CONTEXT", "main": "DF_MAIN", "accent": "DF_ACCENT"}
        conflicts: list[EditorialConflictDetail] = []
        for track in range(1, int(self.timeline.GetTrackCount("video")) + 1):
            track_name = str(self.timeline.GetTrackName("video", track) or "")
            if track_name not in names.values():
                continue
            role = next(r for r, n in names.items() if n == track_name)
            for item in self._iter_values(self.timeline.GetItemListInTrack("video", track)):
                item_name = str(item.GetName() or "")
                # Los clips generados por DaVinci Flow (prefijo DF_ o DF__) pertenecen a ejecuciones previas y se reemplazan.
                if item_name.startswith("DF_") or item_name.startswith("DF__"):
                    continue
                item_start = float(item.GetStart())
                item_end = float(item.GetEnd())
                for idx, (cue, decision) in enumerate(zip(self.proposal.snapshot.cues, self.proposal.decisions)):
                    if decision.enabled and role in decision.templates and item_start < cue.end_frame and item_end > cue.start_frame:
                        if not self._name_candidates(item_name).intersection(self.assignments):
                            conflicts.append(
                                EditorialConflictDetail(
                                    track_name=track_name,
                                    track_index=track,
                                    clip_name=item_name,
                                    start_frame=item_start,
                                    end_frame=item_end,
                                    cue_index=idx,
                                    cue_text=cue.text,
                                )
                            )
        if conflicts:
            first = conflicts[0]
            count = len(conflicts)
            plural = f" y {count - 1} colisiones más" if count > 1 else ""
            msg = (
                f"Conflicto en la pista '{first.track_name}' (V{first.track_index}): "
                f"El clip externo '{first.clip_name}' (fotogramas {first.start_frame:g}–{first.end_frame:g}) "
                f"coincide con el subtítulo #{first.cue_index + 1} ('{first.cue_text[:28]}...'){plural}. "
                f"Mueve este clip fuera de las pistas de DaVinci Flow o usa 'Limpiar pistas DF' para vaciarlas."
            )
            raise EditorialConflictError(msg, tuple(conflicts))


    def _find_timeline_item(self, track_type: str, track_index: int, expected_name: str) -> Any:
        matches = [item for item in self._iter_values(self.timeline.GetItemListInTrack(track_type, track_index))
                   if item.GetName() in self._name_candidates(expected_name)]
        if len(matches) > 1:
            raise EditorialError("Hay clips generados duplicados; revisa la muestra antes de reaplicar.")
        if not matches:
            return None
        item = matches[0]
        if track_type == "audio":
            return item
        template = self.assignments[expected_name]
        tool = text_tool(item.GetFusionCompByIndex(1), template.text_tool)
        if tool.GetInput(template.text_input) != self.expected_text[expected_name]:
            raise EditorialError("El texto generado se editó en Resolve. No se sobrescribirá automáticamente.")
        return item

    def _resolve_record_frame(self, frame: float) -> int:
        # Los subtítulos nativos tienen tiempos absolutos; no inferir el origen por magnitud.
        return round(frame)

    def _append_media_item(self, media_item: Any, media_type: int, track_type: str,
                           track_index: int, record_frame: int, duration_frames: float) -> Any:
        duration = round(duration_frames)
        media_pool = self._require_media_pool()
        result = media_pool.AppendToTimeline([{
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

    def _insert_fusion_title(
        self,
        track_index: int,
        start_frame: float,
        end_frame: float,
        text: str,
        role: str,
        theme: ThemeTokens,
        fps: float,
        native_name: str,
        animation_preset: str = "none",
        template_media_item: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        template = self.assignments[native_name]
        duration = round(end_frame - start_frame)
        media = (self.handles[template.id] if template.source == "media_pool"
                 else self._get_carrier_media_item(self._plan_carrier_frames, fps=fps))
        item = self._append_media_item(media, 1, "video", track_index,
                                       round(start_frame), duration)
        try:
            if template.source != "media_pool":
                comp_path = prepare_comp(template, self.temp_root / "editorial_templates")
                if not item.ImportFusionComp(str(comp_path)):
                    raise EditorialError(f"Resolve no pudo importar {template.name}; prepara una composición en el Media Pool.")
            comp = item.GetFusionCompByIndex(1)
            if template.source != "media_pool":
                connect_template_output(comp, template)
            set_template_text(comp, text, template.text_tool, template.text_input)
            target_y = self.target_y_by_native_name.get(native_name)
            if target_y is not None:
                try:
                    tool = text_tool(comp, template.text_tool)
                    tool.SetInput("Center", [0.5, target_y])
                except Exception:
                    pass
            if comp.SetAttrs({"COMPN_GlobalStart": 0, "COMPN_GlobalEnd": duration - 1,
                              "COMPN_RenderStart": 0, "COMPN_RenderEnd": duration - 1}) is False:
                raise EditorialError("La composición rechazó el rango de animación.")
            named = item.SetName(native_name)
            if named is False or item.GetName() != native_name:
                raise EditorialError("Resolve no confirmó la identidad del clip generado.")
            return item
        except Exception:
            self._delete_items([item], require_success=True)
            raise
