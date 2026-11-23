"""Pruebas unitarias para el emparejador semántico y heurístico de B-Rolls."""

import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.assets.broll_catalog import AssetCollection, BRollAsset
from davinci_flow.assets.broll_matcher import (
    match_brolls_heuristic,
    match_brolls_with_ai,
)
from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.model import SubtitleCue


class BRollMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.asset1 = BRollAsset(
            id="asset_01",
            name="codigo_programador.mp4",
            file_path="/media/codigo.mp4",
            asset_type="video",
            tags=("codigo", "programacion", "desarrollo", "software"),
        )
        self.asset2 = BRollAsset(
            id="asset_02",
            name="whoosh_transicion.wav",
            file_path="/media/whoosh.wav",
            asset_type="audio",
            tags=("whoosh", "transicion", "corte"),
        )
        self.collection = AssetCollection(assets=(self.asset1, self.asset2))

        cue1 = SubtitleCue("Aquí tenemos el código de programación software", 0.0, 48.0, 1)
        self.block1 = CaptionBlock(
            id="b1",
            source_cues=(cue1,),
            start_frame=0.0,
            end_frame=48.0,
            original_text=cue1.text,
            normalized_text=cue1.text,
            main_text="Aquí tenemos el código de programación",
            context_text="En este video",
            accent_text="software",
        )
        cue2 = SubtitleCue("Cocinando un plato delicioso", 50.0, 100.0, 1)
        self.block2 = CaptionBlock(
            id="b2",
            source_cues=(cue2,),
            start_frame=50.0,
            end_frame=100.0,
            original_text=cue2.text,
            normalized_text=cue2.text,
            main_text="Cocinando un plato delicioso",
        )

    def test_match_brolls_heuristic_matches_relevant_block(self) -> None:
        proposals = match_brolls_heuristic([self.block1, self.block2], self.collection)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].block_index, 1)
        self.assertEqual(proposals[0].asset.id, "asset_01")
        self.assertEqual(proposals[0].target_track, "DF_BROLL")

    @patch("davinci_flow.assets.broll_matcher.GeminiClient")
    def test_match_brolls_with_ai_success(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.generate_json.return_value = [
            {
                "block_index": 1,
                "asset_id": "asset_01",
                "reason": "El diálogo menciona código y desarrollo",
            }
        ]
        mock_client_cls.return_value = mock_client

        proposals = match_brolls_with_ai(
            [self.block1, self.block2],
            self.collection,
            api_key="AIzaSyTestKey",
        )
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].block_index, 1)
        self.assertEqual(proposals[0].asset.id, "asset_01")
        self.assertIn("código", proposals[0].reason)


if __name__ == "__main__":
    unittest.main()
