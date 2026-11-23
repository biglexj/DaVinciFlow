from davinci_flow.user_data import user_data_dir
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from davinci_flow.editorial.model import EditorialConflictDetail, EditorialConflictError, EditorialError, Proposal
from davinci_flow.editorial.sources import basic_titles
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.themes.tokens import ThemeTokens
from davinci_flow.editorial.template_files import ROOT_TOOL, template_bytes
from davinci_flow.editorial.native_template import import_native_template


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


def _configured_resource_folders(paths: dict[str, str] | None = None) -> dict[str, list[Path]]:
    folders: dict[str, list[Path]] = {"sfx": [], "visuals": []}
    if paths is None:
        from davinci_flow.editorial.preferences import Preferences
        from davinci_flow.user_data import is_development

        merged_paths = dict(Preferences.load().paths)
        base = user_data_dir()
        gpui_files = (
            sorted(base.parent.glob("gpui-*/library.json"))
            if is_development()
            else [base / "gpui" / "library.json"]
        )
        for gpui_file in gpui_files:
            if not gpui_file.is_file():
                continue
            try:
                data = json.loads(gpui_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            raw_folders = data.get("folders") if isinstance(data, dict) else None
            if not isinstance(raw_folders, dict):
                continue
            for cat in ("sfx", "visuals"):
                entries = raw_folders.get(cat)
                if isinstance(entries, list) and entries:
                    extra = "; ".join(str(p).strip() for p in entries if str(p).strip())
                    if extra:
                        merged_paths[cat] = "; ".join(
                            part for part in (merged_paths.get(cat, ""), extra) if part
                        )
        paths = merged_paths

    for category in ("sfx", "visuals"):
        raw = str(paths.get(category, "") or "").strip()
        if not raw:
            continue
        seen: set[Path] = set()
        for entry in re.split(r"[;\n\r]+", raw):
            cleaned = entry.strip()
            if not cleaned:
                continue
            folder = Path(cleaned).expanduser()
            if folder.is_dir():
                resolved = folder.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    folders[category].append(resolved)
    return folders


def _find_resource_in_folders(name: str, folders: list[Path]) -> Path | None:
    rel_normalized = name.replace("\\", "/").strip()
    if not rel_normalized:
        return None
    target_filename = Path(rel_normalized).name.casefold()
    for folder in folders:
        try:
            direct = (folder / rel_normalized).resolve()
        except OSError:
            continue
        if direct.is_relative_to(folder) and direct.is_file():
            return direct
    for folder in folders:
        for directory, subdirs, files in os.walk(folder, followlinks=False):
            subdirs[:] = sorted(d for d in subdirs if not d.startswith("."))
            for file_name in sorted(files):
                candidate = Path(directory, file_name)
                try:
                    rel = candidate.relative_to(folder).as_posix()
                except ValueError:
                    rel = file_name
                if rel.casefold() == rel_normalized.casefold() or file_name.casefold() == target_filename:
                    if candidate.is_file():
                        return candidate.resolve()
    return None


def resolve_user_resource_paths(
    proposal: Proposal,
    paths: dict[str, str] | None = None,
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Mapea resource_id de recursos de usuario (SFX y B-Rolls) a rutas reales en disco."""
    sfx_paths: dict[str, Path] = {}
    broll_paths: dict[str, Path] = {}
    if proposal.options is None or not proposal.options.resources:
        return sfx_paths, broll_paths

    needed = [
        item for item in proposal.options.resources
        if isinstance(item, dict)
        and item.get("category") in ("sfx", "visuals")
        and item.get("id")
        and item.get("name")
    ]
    if not needed:
        return sfx_paths, broll_paths

    folders = _configured_resource_folders(paths)
    for item in needed:
        rid = str(item["id"]).strip()
        rname = str(item["name"]).strip()
        rcat = str(item["category"]).strip()
        matched = _find_resource_in_folders(rname, folders.get(rcat, []))
        if matched is not None:
            if rcat == "sfx":
                sfx_paths[rid] = matched
            else:
                broll_paths[rid] = matched
    return sfx_paths, broll_paths


class EditorialWriter(ResolveTimelineWriter):
    def __init__(self, timeline: Any, media_pool: Any, proposal: Proposal,
                 handles: dict[str, Any], **kwargs: Any) -> None:
        kwargs.setdefault("temp_root", user_data_dir() / "generated")
        super().__init__(timeline, media_pool, **kwargs)
        fresh_basic = {t.id: t for t in basic_titles()}
        synced_templates = tuple(fresh_basic.get(t.id, t) for t in proposal.templates)
        if synced_templates != proposal.templates:
            proposal = replace(proposal, templates=synced_templates)
        self.proposal = proposal
        self.templates = {t.id: t for t in proposal.templates}
        self.handles = handles
        self.native_templates = {}
        self.user_sfx_paths, self.user_broll_paths = resolve_user_resource_paths(proposal)
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
        has_broll = any(
            d.enabled and d.resource_id in self.user_broll_paths
            for d in self.proposal.decisions
        )
        broll_index = None
        if has_broll:
            v_count = int(self.timeline.GetTrackCount("video"))
            for idx in range(1, v_count + 1):
                if str(self.timeline.GetTrackName("video", idx)) == "DF_BROLL":
                    broll_index = idx
                    break
            text_names = {"DF_CONTEXT", "DF_MAIN", "DF_ACCENT"}
            has_text_tracks = any(
                str(self.timeline.GetTrackName("video", idx)) in text_names
                for idx in range(1, v_count + 1)
            )
            if broll_index is None and not has_text_tracks and self.timeline.AddTrack("video") is True:
                v_count += 1
                self.timeline.SetTrackName("video", v_count, "DF_BROLL")
                broll_index = v_count

        mapping = self.ensure_text_tracks()
        if has_broll:
            if broll_index is None:
                v_count = int(self.timeline.GetTrackCount("video"))
                for idx in range(1, v_count + 1):
                    if str(self.timeline.GetTrackName("video", idx)) == "DF_BROLL":
                        broll_index = idx
                        break
                if broll_index is None and self.timeline.AddTrack("video") is True:
                    v_count += 1
                    self.timeline.SetTrackName("video", v_count, "DF_BROLL")
                    broll_index = v_count
            if broll_index is not None:
                mapping["DF_BROLL"] = broll_index

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
        """Crea solo las pistas de texto requeridas por el modo; nunca renombra una pista existente ajena."""
        track_mode = self.proposal.options.track_mode if self.proposal.options else "triple"
        if track_mode == "single":
            names = ("DF_MAIN",)
        elif track_mode == "dual":
            names = ("DF_MAIN", "DF_ACCENT")
        else:
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
            elif name != "DF_BROLL":
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

        if track_mode == "single":
            mapping["DF_CONTEXT"] = mapping["DF_MAIN"]
            mapping["DF_ACCENT"] = mapping["DF_MAIN"]
        elif track_mode == "dual":
            mapping["DF_CONTEXT"] = mapping["DF_MAIN"]

        return mapping


    def clean_previous_df_clips(self) -> int:
        """Elimina clips de DaVinci Flow (prefijo DF_) en pistas exclusivas que solapen con el bloque activo para admitir iteraciones sucesivas sin alterar otros bloques."""
        if not self.proposal.snapshot.cues:
            return 0
        block_start = float(self.proposal.snapshot.cues[0].start_frame)
        block_end = float(self.proposal.snapshot.cues[-1].end_frame)

        names = {"DF_BROLL", "DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_SFX"}
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
            if template.source not in {'media_pool', 'installed_bin'}:
                raise EditorialError(
                    f'{template.name} está disponible para consulta. Prepara un título nativo en el '
                    'Media Pool o elige una plantilla DRB antes de aplicar. No se creará un vídeo portador.'
                )
            if template.source == "media_pool":
                if template.id not in self.handles:
                    raise EditorialError(f"Ya no existe la plantilla {template.name} en DaVinci Flow.")
            elif template.source != "native":
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
        if track_type == "audio" or expected_name not in self.assignments:
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
                           track_index: int, record_frame: int, duration_frames: float,
                           *, allow_still_default_duration: bool = False) -> Any:
        duration = round(duration_frames)
        source_duration = duration
        if media_type == 1:
            get_property = getattr(media_item, 'GetClipProperty', None)
            clip_type = str(get_property('Type') or '').lower() if callable(get_property) else ''
            is_still = any(tok in clip_type for tok in ('still', 'captura', 'imagen', 'image'))
            if not is_still:
                raw_fps = get_property('FPS') if callable(get_property) else None
                try:
                    source_fps = float(raw_fps) if raw_fps is not None and str(raw_fps).strip() else 0.0
                except (TypeError, ValueError):
                    source_fps = 0.0
                timeline_fps = float(getattr(self.proposal.snapshot, 'fps', 0.0) or 0.0)
                if source_fps > 0 and timeline_fps > 0 and abs(source_fps - timeline_fps) > 0.001:
                    source_duration = max(1, round(duration * source_fps / timeline_fps))
                frames = get_property('Frames') if callable(get_property) else None
                if isinstance(frames, (str, int, float)):
                    try:
                        available = float(frames)
                    except ValueError:
                        available = 0
                    if available > 0 and source_duration > available:
                        raise EditorialError(
                            f'La base nativa tiene {available:g} fotogramas y se solicitaron {source_duration}. '
                            'Prepara una base con duración suficiente antes de aplicar.'
                        )
        media_pool = self._require_media_pool()
        result = media_pool.AppendToTimeline([{
            "mediaPoolItem": media_item, "mediaType": media_type, "trackIndex": track_index,
            # Resolve 21.0.0b.33 comprobado: endFrame=46 produce duración 46, no 47.
            "recordFrame": record_frame, "startFrame": 0, "endFrame": source_duration,
        }])
        items = list(self._iter_values(result))
        if len(items) != 1:
            if items:
                self._delete_items(items, require_success=True)
            raise EditorialError("Resolve no devolvió exactamente un clip.")
        try:
            self._verify_native_item(
                items[0],
                track_type,
                track_index,
                record_frame,
                duration,
                allow_still_default_duration=allow_still_default_duration,
            )
            return items[0]
        except Exception:
            self._delete_items(items, require_success=True)
            raise

    def _verify_native_item(self, item: Any, track_type: str, track_index: int,
                            record_frame: int, duration_frames: float,
                            *, allow_still_default_duration: bool = False) -> None:
        track = item.GetTrackTypeAndIndex()
        if not isinstance(track, (list, tuple)) or list(track) != [track_type, track_index]:
            raise EditorialError("Resolve no confirmó la pista de destino.")
        start_val = item.GetStart()
        if not isinstance(start_val, (int, float)) or abs(start_val - record_frame) > 0.01:
            raise EditorialError("Resolve no confirmó posición y duración exactas.")
        dur_val = item.GetDuration()
        if allow_still_default_duration:
            if not isinstance(dur_val, (int, float)) or dur_val < 1:
                raise EditorialError("Resolve no confirmó posición y duración exactas.")
            return
        duration_tol = 1.01 if track_type == "audio" else 0.01
        if not isinstance(dur_val, (int, float)) or abs(dur_val - round(duration_frames)) > duration_tol:
            raise EditorialError("Resolve no confirmó posición y duración exactas.")

    def _insert_broll_clip(
        self,
        file_path: str,
        track_index: int,
        start_frame: float,
        end_frame: float,
        native_name: str,
    ) -> Any:
        media_pool = self._require_media_pool()
        root_folder = self._safe_call(media_pool, "GetRootFolder")
        target_path = Path(file_path)
        media_item = self._find_media_pool_item(root_folder, target_path.name)
        if media_item is None:
            media_item = self._import_media(target_path)

        duration_frames = max(1, round(end_frame - start_frame))
        get_prop = getattr(media_item, "GetClipProperty", None)
        clip_type = str(get_prop("Type") or "").lower() if callable(get_prop) else ""
        is_still = (
            any(tok in clip_type for tok in ("still", "captura", "imagen", "image"))
            or target_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
        )
        if not is_still and callable(get_prop):
            raw_fps = get_prop("FPS")
            try:
                source_fps = float(raw_fps) if raw_fps is not None and str(raw_fps).strip() else 0.0
            except (TypeError, ValueError):
                source_fps = 0.0
            timeline_fps = float(getattr(self.proposal.snapshot, "fps", 0.0) or 0.0)
            raw_frames = get_prop("Frames")
            try:
                available = float(raw_frames) if raw_frames is not None else 0.0
            except (TypeError, ValueError):
                available = 0.0
            if available > 0:
                available_tl = (
                    int(available * timeline_fps / source_fps)
                    if source_fps > 0 and timeline_fps > 0
                    else int(available)
                )
                if duration_frames > available_tl:
                    duration_frames = max(1, available_tl)

        item = self._append_media_item(
            media_item=media_item,
            media_type=1,
            track_type="video",
            track_index=track_index,
            record_frame=self._resolve_record_frame(start_frame),
            duration_frames=duration_frames,
            allow_still_default_duration=is_still,
        )
        try:
            named = item.SetName(native_name)
            if named is False or item.GetName() != native_name:
                raise EditorialError("Resolve no confirmó la identidad del clip B-Roll.")
            return item
        except Exception:
            self._delete_items([item], require_success=True)
            raise

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

        if template.source == "installed_bin":
            if template.id not in self.native_templates:
                self.native_templates[template.id] = import_native_template(self._require_media_pool(), template)
            media = self.native_templates[template.id]
        elif template.source == "media_pool":
            media = self.handles[template.id]
        else:
            raise EditorialError(
                f'{template.name} está disponible para consulta, pero todavía no tiene una base nativa '
                'para inserción exacta. Elige un título DRB o una plantilla del Media Pool. '
                'No se creará un vídeo portador con Fusion.'
            )
        item = self._append_media_item(media, 1, "video", track_index,
                                       round(start_frame), duration)
        try:
            comp = item.GetFusionCompByIndex(1)
            set_template_text(comp, text, template.text_tool, template.text_input)
            # Conservar geometría, tipografía y animación de la plantilla elegida.
            named = item.SetName(native_name)
            if named is False or item.GetName() != native_name:
                raise EditorialError("Resolve no confirmó la identidad del clip generado.")
            return item
        except Exception:
            self._delete_items([item], require_success=True)
            raise
