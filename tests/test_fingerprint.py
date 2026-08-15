"""Pruebas unitarias para cálculo de huellas e identificadores estables."""

import unittest

from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.fingerprint import (
    compute_blocks_fingerprint,
    compute_cues_fingerprint,
    generate_stable_block_id,
)
from davinci_flow.subtitles.model import SubtitleCue


class FingerprintTests(unittest.TestCase):
    """Verifica la estabilidad, idempotencia y sensibilidad de las huellas criptográficas."""

    def test_cues_fingerprint_is_deterministic(self) -> None:
        cues_a = [
            SubtitleCue(text="Bloque uno", start_frame=0.0, end_frame=50.0, track_index=1),
            SubtitleCue(text="Bloque dos", start_frame=60.0, end_frame=100.0, track_index=1),
        ]
        cues_b = [
            SubtitleCue(text="Bloque uno", start_frame=0.0, end_frame=50.0, track_index=1),
            SubtitleCue(text="Bloque dos", start_frame=60.0, end_frame=100.0, track_index=1),
        ]
        self.assertEqual(compute_cues_fingerprint(cues_a), compute_cues_fingerprint(cues_b))

    def test_cues_fingerprint_changes_on_text_modification(self) -> None:
        cues_a = [SubtitleCue(text="Texto original", start_frame=0.0, end_frame=50.0, track_index=1)]
        cues_b = [SubtitleCue(text="Texto modificado", start_frame=0.0, end_frame=50.0, track_index=1)]
        self.assertNotEqual(compute_cues_fingerprint(cues_a), compute_cues_fingerprint(cues_b))

    def test_cues_fingerprint_changes_on_frame_modification(self) -> None:
        cues_a = [SubtitleCue(text="Mismo texto", start_frame=0.0, end_frame=50.0, track_index=1)]
        cues_b = [SubtitleCue(text="Mismo texto", start_frame=10.0, end_frame=60.0, track_index=1)]
        self.assertNotEqual(compute_cues_fingerprint(cues_a), compute_cues_fingerprint(cues_b))

    def test_stable_block_id_format(self) -> None:
        block_id = generate_stable_block_id(
            track_index=1,
            order_index=5,
            start_frame=120.0,
            end_frame=240.0,
            text="Prueba de identificador",
        )
        self.assertTrue(block_id.startswith("df_t1_b0005_120_240_"))
        self.assertEqual(len(block_id.split("_")[-1]), 8)

    def test_blocks_fingerprint_is_deterministic(self) -> None:
        cue = SubtitleCue(text="Ejemplo", start_frame=0.0, end_frame=24.0, track_index=1)
        block = CaptionBlock(
            id="block_1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=24.0,
            original_text="Ejemplo",
            normalized_text="Ejemplo",
            main_text="Ejemplo",
        )
        hash1 = compute_blocks_fingerprint([block])
        hash2 = compute_blocks_fingerprint([block])
        self.assertEqual(hash1, hash2)


if __name__ == "__main__":
    unittest.main()
