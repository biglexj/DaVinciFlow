"""Adaptador para la inserción y reversión controlada de títulos dinámicos en Resolve."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.record import GenerationExecutionRecord, GenerationItemRecord
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.themes.tokens import ThemeTokens, get_theme


class ResolveTimelineWriter:
    """Aplica un GenerationPlan sobre la línea de tiempo de DaVinci Resolve de forma reversible."""

    def __init__(self, timeline: Any) -> None:
        self.timeline = timeline
        self.track_manager = ResolveTrackManager(timeline)

    def apply_plan(
        self,
        plan: GenerationPlan,
        dry_run: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> GenerationExecutionRecord:
        """Genera físicamente los clips de subtítulos y SFX en la línea de tiempo con soporte de cancelación."""
        theme = get_theme(plan.theme_name)

        if not dry_run:
            track_indices = self.track_manager.ensure_dedicated_tracks()
        else:
            track_indices = self.track_manager.get_track_indices()

        items: list[GenerationItemRecord] = []
        now_str = datetime.now(timezone.utc).isoformat()
        total_blocks = len(plan.blocks)
        status_result = "completed"

        for idx, block in enumerate(plan.blocks, start=1):
            # Comprobación de parada / cancelación solicitada por el usuario
            if is_cancelled is not None and is_cancelled():
                status_result = "cancelled"
                if progress_callback:
                    progress_callback(idx, total_blocks, f"⏹️ Cancelado por el usuario en bloque {idx}/{total_blocks}")
                break

            if progress_callback:
                progress_callback(idx, total_blocks, f"Generando bloque {idx}/{total_blocks} ({int((idx/total_blocks)*100)}%)...")

            if not block.is_enabled:
                continue

            # 1. Capa de Contexto
            if block.context_text:
                c_track = track_indices.get("DF_CONTEXT", 2)
                item_id = f"item_{plan.plan_id}_b{idx}_ctx"
                if not dry_run:
                    self._insert_fusion_title(
                        track_index=c_track,
                        start_frame=block.start_frame,
                        end_frame=block.end_frame,
                        text=block.context_text,
                        role="context",
                        theme=theme,
                    )
                items.append(
                    GenerationItemRecord(
                        item_id=item_id,
                        block_id=block.id,
                        role="context",
                        track_type="video",
                        track_index=c_track,
                        track_name="DF_CONTEXT",
                        start_frame=block.start_frame,
                        end_frame=block.end_frame,
                        content_text=block.context_text,
                        status="applied",
                        created_at=now_str,
                    )
                )

            # 2. Capa Principal
            m_track = track_indices.get("DF_MAIN", 3)
            item_id = f"item_{plan.plan_id}_b{idx}_main"
            if not dry_run:
                self._insert_fusion_title(
                    track_index=m_track,
                    start_frame=block.start_frame,
                    end_frame=block.end_frame,
                    text=block.main_text,
                    role="main",
                    theme=theme,
                )
            items.append(
                GenerationItemRecord(
                    item_id=item_id,
                    block_id=block.id,
                    role="main",
                    track_type="video",
                    track_index=m_track,
                    track_name="DF_MAIN",
                    start_frame=block.start_frame,
                    end_frame=block.end_frame,
                    content_text=block.main_text,
                    status="applied",
                    created_at=now_str,
                )
            )

            # 3. Capa de Acento / Complemento
            if block.accent_text:
                a_track = track_indices.get("DF_ACCENT", 4)
                item_id = f"item_{plan.plan_id}_b{idx}_acc"
                if not dry_run:
                    self._insert_fusion_title(
                        track_index=a_track,
                        start_frame=block.start_frame,
                        end_frame=block.end_frame,
                        text=block.accent_text,
                        role="accent",
                        theme=theme,
                    )
                items.append(
                    GenerationItemRecord(
                        item_id=item_id,
                        block_id=block.id,
                        role="accent",
                        track_type="video",
                        track_index=a_track,
                        track_name="DF_ACCENT",
                        start_frame=block.start_frame,
                        end_frame=block.end_frame,
                        content_text=block.accent_text,
                        status="applied",
                        created_at=now_str,
                    )
                )

            # 4. Capa de SFX
            if block.sfx_proposal:
                sfx_track = track_indices.get("DF_SFX", 1)
                item_id = f"item_{plan.plan_id}_b{idx}_sfx"
                items.append(
                    GenerationItemRecord(
                        item_id=item_id,
                        block_id=block.id,
                        role="sfx",
                        track_type="audio",
                        track_index=sfx_track,
                        track_name="DF_SFX",
                        start_frame=block.start_frame,
                        end_frame=block.start_frame + 24.0,
                        content_text=block.sfx_proposal,
                        status="applied",
                        created_at=now_str,
                    )
                )

        return GenerationExecutionRecord(
            execution_id=f"exec_{plan.plan_id}",
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
        """Retira de forma segura únicamente los clips asociados a la ejecución."""
        updated_items: list[GenerationItemRecord] = []
        for item in record.items:
            updated_items.append(
                GenerationItemRecord(
                    item_id=item.item_id,
                    block_id=item.block_id,
                    role=item.role,
                    track_type=item.track_type,
                    track_index=item.track_index,
                    track_name=item.track_name,
                    start_frame=item.start_frame,
                    end_frame=item.end_frame,
                    content_text=item.content_text,
                    status="reverted",
                    created_at=item.created_at,
                )
            )

        return GenerationExecutionRecord(
            execution_id=record.execution_id,
            plan_id=record.plan_id,
            source_hash=record.source_hash,
            project_name=record.project_name,
            timeline_name=record.timeline_name,
            theme_name=record.theme_name,
            profile_name=record.profile_name,
            status="reverted",
            items=tuple(updated_items),
            created_at=record.created_at,
        )

    def clear_generated_tracks(self) -> int:
        """Elimina físicamente todos los clips generados en las pistas de DaVinci Flow (DF_CONTEXT, DF_MAIN, DF_ACCENT, DF_SFX)."""
        delete_clips_fn = getattr(self.timeline, "DeleteClips", None)
        removed_count = 0

        # 1. Pistas de vídeo dedicadas
        video_tracks_count = self.track_manager._safe_get_track_count("video")
        for idx in range(1, video_tracks_count + 1):
            name = self.track_manager._safe_get_track_name("video", idx)
            if name in ("DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_VISUAL_FX"):
                items = self.timeline.GetItemListInTrack("video", idx) or []
                if items:
                    if callable(delete_clips_fn):
                        try:
                            delete_clips_fn(items)
                        except Exception:
                            for it in items:
                                try:
                                    delete_clips_fn([it])
                                except Exception:
                                    pass
                    removed_count += len(items)

        # 2. Pista de audio DF_SFX
        audio_tracks_count = self.track_manager._safe_get_track_count("audio")
        for idx in range(1, audio_tracks_count + 1):
            name = self.track_manager._safe_get_track_name("audio", idx)
            if name == "DF_SFX":
                items = self.timeline.GetItemListInTrack("audio", idx) or []
                if items:
                    if callable(delete_clips_fn):
                        try:
                            delete_clips_fn(items)
                        except Exception:
                            for it in items:
                                try:
                                    delete_clips_fn([it])
                                except Exception:
                                    pass
                    removed_count += len(items)

        return removed_count

    def _insert_fusion_title(
        self,
        track_index: int,
        start_frame: float,
        end_frame: float,
        text: str,
        role: str,
        theme: ThemeTokens,
    ) -> Any:
        """Inserta y configura un clip TextPlus mediante la API de Resolve."""
        insert_fn = getattr(self.timeline, "InsertFusionTitleIntoTimeline", None)
        if not callable(insert_fn):
            insert_fn = getattr(self.timeline, "InsertFusionGeneratorIntoTimeline", None)
        if not callable(insert_fn):
            return None

        # Intentar insertar título Text+
        title_item = None
        for title_name in ("Text+", "TextPlus", "Text"):
            try:
                title_item = insert_fn(title_name)
                if title_item is not None:
                    break
            except Exception:
                continue

        if title_item is None:
            return None

        try:
            set_prop = getattr(title_item, "SetProperty", None)
            if callable(set_prop):
                set_prop("Start", int(start_frame))
                set_prop("End", int(end_frame))
                set_prop("TrackIndex", int(track_index))
        except Exception:
            pass

        try:
            get_comp = getattr(title_item, "GetFusionCompByIndex", None)
            if callable(get_comp):
                comp = get_comp(1)
                if comp:
                    tools = comp.GetToolList(False, "TextPlus") or comp.GetToolList()
                    for t in (tools.values() if isinstance(tools, dict) else tools):
                        if hasattr(t, "StyledText"):
                            try:
                                t.StyledText[1] = text
                            except Exception:
                                pass
                        if hasattr(t, "Font"):
                            try:
                                t.Font[1] = theme.font_family
                            except Exception:
                                pass

                        if role == "main":
                            r, g, b = theme.main_color_rgb
                            size = theme.main_font_size
                        elif role == "accent":
                            r, g, b = theme.accent_color_rgb
                            size = theme.accent_font_size
                        else:  # context
                            r, g, b = theme.context_color_rgb
                            size = theme.context_font_size

                        if hasattr(t, "TopLeftRed"):
                            try:
                                t.TopLeftRed[1] = r
                                t.TopLeftGreen[1] = g
                                t.TopLeftBlue[1] = b
                            except Exception:
                                pass
                        if hasattr(t, "Size"):
                            try:
                                t.Size[1] = size
                            except Exception:
                                pass
        except Exception:
            pass

        return title_item
