"""Motor de emparejamiento semántico y propuestas contextuales de B-Rolls y SFX."""

import json
from typing import Sequence

from davinci_flow.ai.client import GeminiClient
from davinci_flow.assets.broll_catalog import (
    AssetCollection,
    BRollProposal,
)
from davinci_flow.subtitles.block import CaptionBlock


def match_brolls_heuristic(
    blocks: Sequence[CaptionBlock],
    collection: AssetCollection,
    min_score: float = 2.0,
) -> list[BRollProposal]:
    """Genera propuestas de B-Roll cruzando el contenido de los bloques con los tags de los assets."""
    if not blocks or collection.total_count == 0:
        return []

    proposals: list[BRollProposal] = []
    used_asset_ids: set[str] = set()

    for idx, block in enumerate(blocks, start=1):
        if not block.is_enabled:
            continue

        # Palabras de todos los textos del bloque
        full_text = f"{block.context_text} {block.main_text} {block.accent_text}".lower()
        words = [w for w in full_text.split() if len(w) >= 3]

        best_asset, score = collection.find_best_match(
            query_terms=words,
            asset_type="video",
            min_score=min_score,
        )

        if best_asset and best_asset.id not in used_asset_ids:
            used_asset_ids.add(best_asset.id)
            proposals.append(
                BRollProposal(
                    block_index=idx,
                    asset=best_asset,
                    start_frame=block.start_frame,
                    end_frame=block.end_frame,
                    target_track="DF_BROLL",
                    reason=f"Coincidencia temática con '{best_asset.name}'",
                    score=score,
                )
            )

    return proposals


def match_brolls_with_ai(
    blocks: Sequence[CaptionBlock],
    collection: AssetCollection,
    api_key: str | None = None,
    model_name: str = "gemini-2.5-flash",
) -> list[BRollProposal]:
    """Utiliza Gemini para analizar el contexto narrativo y seleccionar los mejores B-Rolls y sonidos de apoyo."""
    if not blocks or collection.total_count == 0:
        return []

    # Si hay muy pocos assets o no hay cliente, fallback a heurística
    try:
        client = GeminiClient(api_key=api_key, model_name=model_name)
    except Exception:
        return match_brolls_heuristic(blocks, collection)

    catalog_data = [
        {
            "id": a.id,
            "name": a.name,
            "type": a.asset_type,
            "tags": list(a.tags),
        }
        for a in collection.assets
    ]

    blocks_data = [
        {
            "index": idx,
            "time_frames": f"{b.start_frame:g}-{b.end_frame:g}",
            "text": b.main_text,
        }
        for idx, b in enumerate(blocks, start=1)
        if b.is_enabled
    ]

    prompt = f"""Eres un editor de vídeo profesional y diseñador de sonido en DaVinci Resolve.
Tu tarea es emparejar clips de apoyo (B-Rolls de vídeo o efectos de sonido especiales) con fragmentos del diálogo según el contexto semántico y ritmo narrativo.

RECURSOS DISPONIBLES:
{json.dumps(catalog_data, ensure_ascii=False, indent=2)}

FRAGMENTOS DE DIÁLOGO / TRANSCRIPCIÓN:
{json.dumps(blocks_data, ensure_ascii=False, indent=2)}

INSTRUCCIONES:
1. No fuerces un B-Roll en cada bloque. Úsalos con criterio editorial cuando el diálogo hable directamente del tema del clip o haya un cambio de tema importante.
2. Devuelve un array JSON de propuestas con la estructura exacta:
[
  {{
    "block_index": 1,
    "asset_id": "id_del_asset",
    "reason": "Explicación breve de por qué encaja editorialmente"
  }}
]
Si ningún recurso encaja, devuelve una lista vacía [].
"""

    try:
        raw_result = client.generate_json(
            prompt=prompt,
            system_instruction="Eres un asistente experto en montaje de B-Rolls y diseño sonoro en DaVinci Resolve.",
            temperature=0.2,
        )

        if not isinstance(raw_result, list):
            return match_brolls_heuristic(blocks, collection)

        assets_by_id = {a.id: a for a in collection.assets}
        blocks_by_idx = {
            idx: b
            for idx, b in enumerate(blocks, start=1)
        }

        proposals: list[BRollProposal] = []
        for item in raw_result:
            if not isinstance(item, dict):
                continue
            b_idx = int(item.get("block_index", 0))
            a_id = str(item.get("asset_id", "")).strip()
            reason = str(item.get("reason", "Propuesta asistida por IA")).strip()

            if b_idx in blocks_by_idx and a_id in assets_by_id:
                target_block = blocks_by_idx[b_idx]
                target_asset = assets_by_id[a_id]
                target_track = "DF_BROLL" if target_asset.asset_type == "video" else "DF_SFX"

                proposals.append(
                    BRollProposal(
                        block_index=b_idx,
                        asset=target_asset,
                        start_frame=target_block.start_frame,
                        end_frame=target_block.end_frame,
                        target_track=target_track,
                        reason=reason,
                        score=3.0,
                    )
                )

        return proposals if proposals else match_brolls_heuristic(blocks, collection)

    except Exception:
        return match_brolls_heuristic(blocks, collection)
