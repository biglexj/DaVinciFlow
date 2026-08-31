"""Motor de propuesta de SFX según intención narrativa, detección de pausas y límites de densidad."""

from typing import Sequence

from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS, AssetDescriptor, SFXCatalog
from davinci_flow.subtitles.block import CaptionBlock

# Perfiles de densidad y su distancia mínima en fotogramas entre efectos sucesivos
PROFILE_COOLDOWNS = {
    "reflexivo": 180.0,    # ~7.5s a 24fps
    "natural": 84.0,       # ~3.5s a 24fps
    "educativo": 72.0,     # ~3.0s a 24fps
    "dinamico": 42.0,      # ~1.75s a 24fps
    "video_corto": 28.0,   # ~1.15s a 24fps
}


class SFXProposalEngine:
    """Calcula deterministamente propuestas de efectos sonoros respetando la densidad, la intención y pausas."""

    def __init__(self, catalog: SFXCatalog | None = None) -> None:
        self.catalog = catalog or SFXCatalog()

    def process_blocks(
        self,
        blocks: Sequence[CaptionBlock],
        profile_name: str = "natural",
        disable_sfx: bool = False,
        detect_gaps: bool = True,
        min_gap_frames: float = 24.0,
    ) -> tuple[CaptionBlock, ...]:
        """Asigna propuestas de SFX a los bloques cumpliendo reglas editoriales y de ritmo."""
        if disable_sfx:
            return tuple(
                CaptionBlock(
                    id=b.id,
                    source_cues=b.source_cues,
                    start_frame=b.start_frame,
                    end_frame=b.end_frame,
                    original_text=b.original_text,
                    normalized_text=b.normalized_text,
                    main_text=b.main_text,
                    context_text=b.context_text,
                    accent_text=b.accent_text,
                    intent=b.intent,
                    confidence=b.confidence,
                    reason=b.reason,
                    style_preset=b.style_preset,
                    sfx_proposal=None,
                    is_enabled=b.is_enabled,
                )
                for b in blocks
            )

        prof_lower = profile_name.lower()
        min_cooldown = PROFILE_COOLDOWNS.get(prof_lower, 84.0)
        last_sfx_end = -float("inf")
        prev_block_end = -float("inf")
        result: list[CaptionBlock] = []

        for b in blocks:
            # Si el bloque ya cuenta con un SFX manual explícito, conservarlo si está habilitado
            if b.sfx_proposal and b.is_enabled and "sfx_off" not in b.normalized_text.lower():
                last_sfx_end = b.start_frame
                prev_block_end = b.end_frame
                result.append(b)
                continue

            # Si el bloque contiene la marca explícita SFX_OFF o está inactivo, omitir SFX
            if "sfx_off" in b.normalized_text.lower() or not b.is_enabled:
                prev_block_end = b.end_frame
                result.append(b)
                continue

            # Detección de brecha temporal (pausa/silencio o corte de escena)
            gap_duration = b.start_frame - prev_block_end if prev_block_end > -float("inf") else 0.0
            is_significant_pause = detect_gaps and (gap_duration >= min_gap_frames)

            # Distancia desde el último SFX insertado
            distance_from_last = b.start_frame - last_sfx_end
            if distance_from_last < min_cooldown:
                # Enfriamiento activo: no saturar la mezcla de audio
                prev_block_end = b.end_frame
                result.append(b)
                continue

            # Selección determinista por intención y pausas
            chosen_sfx: str | None = None
            if b.intent == "emphasis":
                chosen_sfx = "sfx_whoosh_clean_01"
            elif b.intent == "question":
                chosen_sfx = "sfx_pop_subtle_01"
            elif b.intent == "exclamation":
                if prof_lower != "reflexivo":
                    chosen_sfx = "sfx_whoosh_clean_01"
            elif is_significant_pause:
                # Transición tras una pausa o cambio de sección
                if prof_lower == "reflexivo":
                    chosen_sfx = "sfx_bell_chime_01"
                elif prof_lower in ("dinamico", "video_corto"):
                    chosen_sfx = "sfx_whoosh_clean_01"
                else:
                    chosen_sfx = "sfx_pop_subtle_01"
            elif b.layer_count >= 2 and distance_from_last >= (min_cooldown * 1.5):
                # Para frases multicapa con separación suficiente
                chosen_sfx = "sfx_click_tech_01"

            prev_block_end = b.end_frame

            if chosen_sfx:
                last_sfx_end = b.start_frame
                # Crear nuevo CaptionBlock con la propuesta de SFX
                updated_block = CaptionBlock(
                    id=b.id,
                    source_cues=b.source_cues,
                    start_frame=b.start_frame,
                    end_frame=b.end_frame,
                    original_text=b.original_text,
                    normalized_text=b.normalized_text,
                    main_text=b.main_text,
                    context_text=b.context_text,
                    accent_text=b.accent_text,
                    intent=b.intent,
                    confidence=b.confidence,
                    reason=b.reason,
                    style_preset=b.style_preset,
                    sfx_proposal=chosen_sfx,
                    is_enabled=b.is_enabled,
                )
                result.append(updated_block)
            else:
                result.append(b)

        return tuple(result)
