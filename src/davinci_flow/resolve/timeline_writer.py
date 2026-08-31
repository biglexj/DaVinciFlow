"""Escritura verificada y reversible sobre la línea de tiempo de Resolve."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from davinci_flow.errors import TimelineWriteError
from davinci_flow.generation.carrier_media import write_black_uncompressed_avi
from davinci_flow.generation.fusion_template import generate_textplus_fusion_setting
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.record import GenerationExecutionRecord, GenerationItemRecord
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.sfx.assets import ensure_builtin_sfx_assets
from davinci_flow.sfx.catalog import SFXCatalog
from davinci_flow.themes.tokens import ThemeTokens, get_theme

_CARRIER_MEDIA_PREFIX = "DF_FUSION_CARRIER_V2"


class ResolveTimelineWriter:
    """Aplica un plan mediante operaciones documentadas y verifica cada resultado nativo."""

    def __init__(
        self,
        timeline: Any,
        media_pool: Any | None = None,
        asset_root: str | Path | None = None,
        temp_root: str | Path | None = None,
        sfx_catalog: SFXCatalog | None = None,
    ) -> None:
        self.timeline = timeline
        self.media_pool = media_pool
        self.track_manager = ResolveTrackManager(timeline)
        self.asset_root = Path(asset_root) if asset_root is not None else None
        self.temp_root = (
            Path(temp_root)
            if temp_root is not None
            else Path(tempfile.gettempdir()) / "DaVinciFlow"
        )
        self.sfx_catalog = sfx_catalog or SFXCatalog()
        self._carrier_media_items: dict[str, Any] = {}
        self._imported_sfx: dict[str, Any] = {}
        self._plan_carrier_frames = 1

    def apply_plan(
        self,
        plan: GenerationPlan,
        dry_run: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> GenerationExecutionRecord:
        """Genera clips reales o una previsualización que nunca se marca como aplicada."""
        theme = get_theme(plan.theme_name)
        track_indices = (
            self.track_manager.get_track_indices()
            if dry_run
            else self.track_manager.ensure_dedicated_tracks()
        )
        execution_id = f"exec_{plan.plan_id}"
        now_str = datetime.now(timezone.utc).isoformat()
        items: list[GenerationItemRecord] = []
        inserted_native_items: list[Any] = []
        total_blocks = len(plan.blocks)
        status_result = "dry_run" if dry_run else "completed"
        self._plan_carrier_frames = max(
            (
                max(1, int(round(block.end_frame - block.start_frame)))
                for block in plan.blocks
                if block.is_enabled
            ),
            default=1,
        )

        try:
            for block_index, block in enumerate(plan.blocks, start=1):
                if is_cancelled is not None and is_cancelled():
                    status_result = "cancelled"
                    if progress_callback:
                        progress_callback(
                            block_index,
                            total_blocks,
                            f"Cancelado por el usuario en el bloque {block_index}/{total_blocks}",
                        )
                    break

                if progress_callback:
                    percentage = int((block_index / max(1, total_blocks)) * 100)
                    progress_callback(
                        block_index,
                        total_blocks,
                        f"Generando bloque {block_index}/{total_blocks} ({percentage} %)...",
                    )

                if not block.is_enabled:
                    continue

                layers = (
                    ("context", "DF_CONTEXT", block.context_text),
                    ("main", "DF_MAIN", block.main_text),
                    ("accent", "DF_ACCENT", block.accent_text),
                )
                for role, track_name, text in layers:
                    if not text:
                        continue
                    item_id = f"item_{plan.plan_id}_b{block_index}_{role[:3]}"
                    track_index = track_indices[track_name]
                    native_item = None
                    if not dry_run:
                        native_name = self._native_name(execution_id, item_id)
                        duration_frames = max(1, int(round(block.end_frame - block.start_frame)))
                        anim_preset = block.style_preset or self._resolve_default_animation(
                            plan.profile_name, role
                        )
                        native_item = self._find_timeline_item("video", track_index, native_name)
                        if native_item is None:
                            native_item = self._insert_fusion_title(
                                track_index=track_index,
                                start_frame=block.start_frame,
                                end_frame=block.end_frame,
                                text=text,
                                role=role,
                                theme=theme,
                                fps=plan.fps,
                                native_name=native_name,
                                animation_preset=anim_preset,
                            )
                            inserted_native_items.append(native_item)
                        else:
                            self._verify_native_item(
                                native_item,
                                "video",
                                track_index,
                                self._resolve_record_frame(block.start_frame),
                                duration_frames,
                            )

                    items.append(
                        GenerationItemRecord(
                            item_id=item_id,
                            block_id=block.id,
                            role=role,
                            track_type="video",
                            track_index=track_index,
                            track_name=track_name,
                            start_frame=block.start_frame,
                            end_frame=block.end_frame,
                            content_text=text,
                            status="planned" if dry_run else "applied",
                            native_item_id=self._get_native_id(native_item),
                            created_at=now_str,
                        )
                    )

                if block.sfx_proposal:
                    item_id = f"item_{plan.plan_id}_b{block_index}_sfx"
                    track_index = track_indices["DF_SFX"]
                    descriptor = self.sfx_catalog.get(block.sfx_proposal)
                    duration_frames = max(1.0, descriptor.duration_seconds * plan.fps)
                    native_item = None
                    if not dry_run:
                        native_name = self._native_name(execution_id, item_id)
                        native_item = self._find_timeline_item("audio", track_index, native_name)
                        if native_item is None:
                            native_item = self._insert_sfx(
                                asset_id=descriptor.id,
                                track_index=track_index,
                                start_frame=block.start_frame,
                                duration_frames=duration_frames,
                                native_name=native_name,
                            )
                            inserted_native_items.append(native_item)
                        else:
                            self._verify_native_item(
                                native_item,
                                "audio",
                                track_index,
                                self._resolve_record_frame(block.start_frame),
                                duration_frames,
                            )

                    items.append(
                        GenerationItemRecord(
                            item_id=item_id,
                            block_id=block.id,
                            role="sfx",
                            track_type="audio",
                            track_index=track_index,
                            track_name="DF_SFX",
                            start_frame=block.start_frame,
                            end_frame=block.start_frame + duration_frames,
                            content_text=descriptor.id,
                            status="planned" if dry_run else "applied",
                            native_item_id=self._get_native_id(native_item),
                            created_at=now_str,
                        )
                    )
        except Exception as error:
            if inserted_native_items:
                self._delete_items(inserted_native_items)
            if isinstance(error, TimelineWriteError):
                raise
            raise TimelineWriteError(f"Resolve rechazó la generación: {error}") from error

        return GenerationExecutionRecord(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            source_hash=plan.source_hash,
            project_name=plan.project_name,
            timeline_name=plan.timeline_name,
            theme_name=plan.theme_name,
            profile_name=plan.profile_name,
            status=status_result,
            items=tuple(items),
            created_at=now_str,
        )

    def revert_execution(self, record: GenerationExecutionRecord) -> GenerationExecutionRecord:
        """Elimina únicamente los clips cuyos identificadores pertenecen a la ejecución."""
        found_by_record_id: dict[str, Any] = {}
        tracks = {
            (item.track_type, item.track_index)
            for item in record.items
            if item.status == "applied"
        }
        for track_type, track_index in tracks:
            get_items = getattr(self.timeline, "GetItemListInTrack", None)
            if not callable(get_items):
                raise TimelineWriteError("Resolve no permite enumerar los clips para deshacer la ejecución.")
            native_items = get_items(track_type, track_index) or []
            for native_item in self._iter_values(native_items):
                native_id = self._get_native_id(native_item)
                native_name = self._safe_call(native_item, "GetName")
                for record_item in record.items:
                    expected_name = self._native_name(record.execution_id, record_item.item_id)
                    if (
                        record_item.status == "applied"
                        and record_item.item_id not in found_by_record_id
                        and (
                            (record_item.native_item_id and native_id == record_item.native_item_id)
                            or native_name == expected_name
                        )
                    ):
                        found_by_record_id[record_item.item_id] = native_item

        if found_by_record_id:
            self._delete_items(found_by_record_id.values(), require_success=True)

        updated_items = tuple(
            replace(
                item,
                status=(
                    "reverted"
                    if item.item_id in found_by_record_id
                    else "missing"
                    if item.status == "applied"
                    else item.status
                ),
            )
            for item in record.items
        )
        revert_status = "partial" if any(item.status == "missing" for item in updated_items) else "reverted"
        return replace(record, status=revert_status, items=updated_items)

    def clear_generated_tracks(self) -> int:
        """Elimina todos los clips de pistas DF; se conserva como limpieza global explícita."""
        collected: list[Any] = []
        for track_type, allowed_names in (
            ("video", {"DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_VISUAL_FX"}),
            ("audio", {"DF_SFX"}),
        ):
            for index in range(1, self.track_manager._safe_get_track_count(track_type) + 1):
                if self.track_manager._safe_get_track_name(track_type, index) not in allowed_names:
                    continue
                items = self.timeline.GetItemListInTrack(track_type, index) or []
                collected.extend(self._iter_values(items))
        if collected:
            self._delete_items(collected, require_success=True)
        return len(collected)

    @staticmethod
    def _resolve_default_animation(profile_name: str, role: str) -> str:
        """Determina la animación por defecto según el perfil editorial y el rol de la capa."""
        p = (profile_name or "natural").lower()
        if p in ("dinamico", "video_corto"):
            if role == "accent":
                return "kinetic_pulse"
            if role == "main":
                return "pop_bounce"
            return "slide_up"
        if p in ("reflexivo", "educativo"):
            if role == "accent":
                return "pop_bounce"
            if role == "main":
                return "fade_smooth"
            return "slide_up"
        if role == "accent":
            return "pop_bounce"
        if role == "context":
            return "slide_up"
        return "pop_bounce"

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
    ) -> Any:
        """Añade un soporte transparente exacto e importa una composición Fusion propia con animación."""
        duration_frames = max(1, int(round(end_frame - start_frame)))
        media_item = self._get_carrier_media_item(self._plan_carrier_frames, fps=fps)
        title_item = self._append_media_item(
            media_item=media_item,
            media_type=1,
            track_type="video",
            track_index=track_index,
            record_frame=self._resolve_record_frame(start_frame),
            duration_frames=duration_frames,
        )
        self._set_native_name(title_item, native_name)

        self.temp_root.mkdir(parents=True, exist_ok=True)
        comp_path = self.temp_root / f"{native_name.replace(':', '_')}.comp"
        comp_text = generate_textplus_fusion_setting(
            text=text,
            tokens=theme,
            role=role,
            animation_preset=animation_preset,
        )
        comp_path.write_text(comp_text, encoding="utf-8")
        try:
            import_comp = getattr(title_item, "ImportFusionComp", None)
            if not callable(import_comp):
                self._delete_items([title_item])
                raise TimelineWriteError("El clip creado no expone ImportFusionComp().")
            composition = import_comp(str(comp_path))
            if composition is None or composition is False:
                self._delete_items([title_item])
                raise TimelineWriteError("Resolve no importó la composición Fusion generada.")
        finally:
            try:
                comp_path.unlink(missing_ok=True)
            except OSError:
                pass

        return title_item

    def _insert_sfx(
        self,
        asset_id: str,
        track_index: int,
        start_frame: float,
        duration_frames: float,
        native_name: str,
    ) -> Any:
        """Importa e inserta un WAV real en la pista DF_SFX con tiempo verificado."""
        media_item = self._imported_sfx.get(asset_id)
        if media_item is None:
            paths = ensure_builtin_sfx_assets(self.asset_root)
            path = paths[asset_id]
            root_folder = self._safe_call(self._require_media_pool(), "GetRootFolder")
            media_item = self._find_media_pool_item(root_folder, path.name)
            if media_item is None:
                media_item = self._import_media(path)
            self._imported_sfx[asset_id] = media_item

        sfx_item = self._append_media_item(
            media_item=media_item,
            media_type=2,
            track_type="audio",
            track_index=track_index,
            record_frame=self._resolve_record_frame(start_frame),
            duration_frames=duration_frames,
        )
        self._set_native_name(sfx_item, native_name)
        return sfx_item

    def _append_media_item(
        self,
        media_item: Any,
        media_type: int,
        track_type: str,
        track_index: int,
        record_frame: int,
        duration_frames: float,
    ) -> Any:
        media_pool = self._require_media_pool()
        append = getattr(media_pool, "AppendToTimeline", None)
        if not callable(append):
            raise TimelineWriteError("El Media Pool no expone AppendToTimeline().")

        clip_info = {
            "mediaPoolItem": media_item,
            "startFrame": 0,
            "endFrame": float(duration_frames),
            "mediaType": media_type,
            "trackIndex": int(track_index),
            "recordFrame": int(record_frame),
        }
        result = append([clip_info])
        native_items = list(self._iter_values(result))
        if not native_items:
            raise TimelineWriteError(
                f"Resolve no creó el clip en {track_type} {track_index} (fotograma {record_frame})."
            )
        item = native_items[0]
        try:
            self._verify_native_item(
                item=item,
                track_type=track_type,
                track_index=track_index,
                record_frame=record_frame,
                duration_frames=duration_frames,
            )
        except Exception:
            self._delete_items([item])
            raise
        return item

    def _verify_native_item(
        self,
        item: Any,
        track_type: str,
        track_index: int,
        record_frame: int,
        duration_frames: float,
    ) -> None:
        track_data = self._safe_call(item, "GetTrackTypeAndIndex")
        if isinstance(track_data, (list, tuple)) and len(track_data) >= 2:
            actual_type, actual_index = str(track_data[0]), int(track_data[1])
            if actual_type != track_type or actual_index != track_index:
                raise TimelineWriteError(
                    f"Resolve insertó el clip en {actual_type} {actual_index}; se esperaba {track_type} {track_index}."
                )

        actual_start = self._numeric_item_call(item, "GetStart")
        if actual_start is not None and abs(actual_start - record_frame) > 0.01:
            raise TimelineWriteError(
                f"Resolve insertó el clip en el fotograma {actual_start:g}; se esperaba {record_frame}."
            )

        actual_duration = self._numeric_item_call(item, "GetDuration")
        if actual_duration is not None and abs(actual_duration - duration_frames) > 0.11:
            raise TimelineWriteError(
                f"Resolve creó una duración de {actual_duration:g} fotogramas; se esperaban {duration_frames}."
            )

    def _get_carrier_media_item(self, minimum_frames: int, fps: float) -> Any:
        fps_label = str(fps).replace(".", "_")
        media_name = f"{_CARRIER_MEDIA_PREFIX}_{fps_label}_{minimum_frames}.avi"
        cached = self._carrier_media_items.get(media_name)
        if cached is not None:
            return cached
        media_pool = self._require_media_pool()
        root_folder = self._safe_call(media_pool, "GetRootFolder")
        existing = self._find_media_pool_item(root_folder, media_name)
        if existing is not None:
            self._carrier_media_items[media_name] = existing
            return existing

        self.temp_root.mkdir(parents=True, exist_ok=True)
        carrier_path = self.temp_root / media_name
        write_black_uncompressed_avi(carrier_path, frame_count=minimum_frames + 1, fps=fps)
        media_item = self._import_media(carrier_path)
        self._carrier_media_items[media_name] = media_item
        return media_item

    def _import_media(self, path: Path) -> Any:
        if not path.is_file():
            raise TimelineWriteError(f"El recurso no existe: {path}")
        media_pool = self._require_media_pool()
        import_media = getattr(media_pool, "ImportMedia", None)
        if not callable(import_media):
            raise TimelineWriteError("El Media Pool no expone ImportMedia().")
        result = import_media([str(path)])
        imported = list(self._iter_values(result))
        if not imported:
            raise TimelineWriteError(f"Resolve no importó el recurso: {path.name}")
        return imported[0]

    def _find_media_pool_item(self, folder: Any, expected_name: str) -> Any | None:
        if folder is None:
            return None
        clips = self._safe_call(folder, "GetClipList") or []
        for clip in self._iter_values(clips):
            if self._safe_call(clip, "GetName") == expected_name:
                return clip
        subfolders = self._safe_call(folder, "GetSubFolderList") or []
        for subfolder in self._iter_values(subfolders):
            found = self._find_media_pool_item(subfolder, expected_name)
            if found is not None:
                return found
        return None

    def _find_timeline_item(self, track_type: str, track_index: int, expected_name: str) -> Any | None:
        get_items = getattr(self.timeline, "GetItemListInTrack", None)
        if not callable(get_items):
            return None
        try:
            items = get_items(track_type, track_index) or []
        except Exception:
            return None
        for item in self._iter_values(items):
            if self._safe_call(item, "GetName") == expected_name:
                return item
        return None

    def _resolve_record_frame(self, frame: float) -> int:
        target = int(round(frame))
        start = self._numeric_call(self.timeline, "GetStartFrame")
        if start is not None and start > 0 and target < start:
            target += int(round(start))
        return target

    def _delete_items(self, items: Iterable[Any], require_success: bool = False) -> None:
        native_items = [item for item in items if item is not None]
        if not native_items:
            return
        delete = getattr(self.timeline, "DeleteClips", None)
        if not callable(delete):
            if require_success:
                raise TimelineWriteError("Resolve no permite eliminar los clips seleccionados.")
            return
        result = delete(native_items, False)
        if require_success and result is False:
            raise TimelineWriteError("Resolve rechazó la eliminación de los clips seleccionados.")

    def _require_media_pool(self) -> Any:
        if self.media_pool is None:
            raise TimelineWriteError(
                "La generación física necesita el Media Pool del proyecto activo."
            )
        return self.media_pool

    @staticmethod
    def _native_name(execution_id: str, item_id: str) -> str:
        return f"DF::{execution_id}::{item_id}"

    @staticmethod
    def _set_native_name(item: Any, name: str) -> None:
        set_name = getattr(item, "SetName", None)
        if callable(set_name):
            set_name(name)

    @staticmethod
    def _get_native_id(item: Any | None) -> str | None:
        if item is None:
            return None
        value = ResolveTimelineWriter._safe_call(item, "GetUniqueId")
        return str(value) if isinstance(value, (str, int)) and str(value) else None

    @staticmethod
    def _safe_call(obj: Any, method_name: str) -> Any:
        method = getattr(obj, method_name, None)
        if not callable(method):
            return None
        try:
            return method()
        except TypeError:
            try:
                return method(False)
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _numeric_call(obj: Any, method_name: str) -> float | None:
        value = ResolveTimelineWriter._safe_call(obj, method_name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    @staticmethod
    def _numeric_item_call(item: Any, method_name: str) -> float | None:
        method = getattr(item, method_name, None)
        if not callable(method):
            return None
        try:
            value = method(True)
        except TypeError:
            try:
                value = method()
            except Exception:
                return None
        except Exception:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    @staticmethod
    def _iter_values(value: Any) -> Iterable[Any]:
        if isinstance(value, dict):
            return value.values()
        if isinstance(value, (list, tuple)):
            return value
        return ()
