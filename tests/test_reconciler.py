"""Pruebas unitarias para el motor de reconciliación y regeneración selectiva."""

import unittest

from davinci_flow.generation.plan import build_generation_plan
from davinci_flow.generation.reconciler import reconcile_subtitles
from davinci_flow.subtitles.model import SubtitleCue


class ReconcilerTests(unittest.TestCase):
    """Verifica la detección de bloques idénticos, modificados, agregados y eliminados."""

    def setUp(self) -> None:
        self.initial_cues = [
            SubtitleCue(text="Subtítulo uno", start_frame=0.0, end_frame=50.0, track_index=1),
            SubtitleCue(text="Subtítulo dos", start_frame=60.0, end_frame=120.0, track_index=1),
        ]
        self.initial_plan = build_generation_plan(
            project_name="Proyecto",
            timeline_name="Timeline",
            cues=self.initial_cues,
            track_index=1,
        )

    def test_identical_cues_reports_is_identical(self) -> None:
        diff = reconcile_subtitles(self.initial_plan, self.initial_cues)
        self.assertTrue(diff.is_identical)
        self.assertEqual(len(diff.added_blocks), 0)
        self.assertEqual(len(diff.modified_blocks), 0)
        self.assertEqual(len(diff.deleted_block_ids), 0)
        self.assertEqual(len(diff.unchanged_blocks), 2)

    def test_detects_added_cue(self) -> None:
        updated_cues = list(self.initial_cues) + [
            SubtitleCue(text="Subtítulo tres nuevo", start_frame=130.0, end_frame=180.0, track_index=1)
        ]
        diff = reconcile_subtitles(self.initial_plan, updated_cues)
        self.assertFalse(diff.is_identical)
        self.assertEqual(len(diff.added_blocks), 1)
        self.assertEqual(len(diff.unchanged_blocks), 2)
        self.assertEqual(diff.added_blocks[0].original_text, "Subtítulo tres nuevo")

    def test_detects_deleted_cue(self) -> None:
        updated_cues = [self.initial_cues[0]]  # Se elimina el segundo
        diff = reconcile_subtitles(self.initial_plan, updated_cues)
        self.assertFalse(diff.is_identical)
        self.assertEqual(len(diff.deleted_block_ids), 1)
        self.assertEqual(len(diff.unchanged_blocks), 1)


if __name__ == "__main__":
    unittest.main()
