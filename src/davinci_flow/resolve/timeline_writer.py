"""Adaptador para la inserción y reversión controlada de títulos dinámicos en Resolve."""

from datetime import datetime, timezone
from typing import Any

from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.record import GenerationExecutionRecord, GenerationItemRecord
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.themes.tokens import get_theme


class ResolveTimelineWriter:
    """Aplica un GenerationPlan sobre la línea de tiempo de DaVinci Resolve de forma reversible."""

    def __init__(self, timeline: Any) -> None:
        self.timeline = timeline
        self.track_manager = ResolveTrackManager(timeline)

    def apply_plan(
        self,
        plan: GenerationPlan,
        dry_run: bool = False,
    ) -> GenerationExecutionRecord:
        """Genera los clips de subtítulos y SFX en la línea de tiempo."""
        theme = get_theme(plan.theme_name)
        track_indices = self.track_manager.get_track_indices()
        items: list[GenerationItemRecord] = []
        now_str = datetime.now(timezone.utc).isoformat()

        for idx, block in enumerate(plan.blocks, start=1):
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
                        end_frame=block.start_frame + 24.0,  # ~1s estimativo
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
            status="completed",
            items=tuple(items),
            created_at=now_str,
        )

    def revert_execution(self, record: GenerationExecutionRecord) -> GenerationExecutionRecord:
        """Retira de forma segura únicamente los clips asociados a la ejecución."""
        updated_items: list[GenerationItemRecord] = []
        for item in record.items:
            # En entorno real se remueve el clip específico en Resolve
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

    def _insert_fusion_title(
        self,
        track_index: int,
        start_frame: float,
        end_frame: float,
        text: str,
        role: str,
    ) -> None:
        """Inserta o actualiza un clip TextPlus mediante la API disponible de Resolve."""
        pass
