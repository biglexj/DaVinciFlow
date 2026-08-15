"""Pruebas unitarias para ResolveTimelineWriter y TrackManager."""

import unittest
from unittest.mock import MagicMock

from davinci_flow.generation.plan import build_generation_plan
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.subtitles.model import SubtitleCue


class TimelineWriterTests(unittest.TestCase):
    """Verifica la inserción multicapa en pistas dedicadas y el comportamiento dry_run."""

    def setUp(self) -> None:
        self.mock_timeline = MagicMock()
        self.mock_timeline.GetTrackCount.side_effect = lambda t: 1
        self.mock_timeline.GetTrackName.side_effect = lambda t, idx: ""

        self.cues = [
            SubtitleCue(
                text="Por lo tanto, DaVinci Flow automatiza con elegancia.",
                start_frame=0.0,
                end_frame=48.0,
                track_index=1,
            )
        ]
        self.plan = build_generation_plan(
            project_name="Proyecto",
            timeline_name="Timeline",
            cues=self.cues,
            track_index=1,
            theme_name="ely",
        )

    def test_track_manager_calculates_dedicated_tracks(self) -> None:
        manager = ResolveTrackManager(self.mock_timeline)
        indices = manager.get_track_indices()
        self.assertIn("DF_CONTEXT", indices)
        self.assertIn("DF_MAIN", indices)
        self.assertIn("DF_ACCENT", indices)
        self.assertIn("DF_SFX", indices)

    def test_apply_plan_dry_run_generates_execution_record(self) -> None:
        writer = ResolveTimelineWriter(self.mock_timeline)
        record = writer.apply_plan(self.plan, dry_run=True)

        self.assertEqual(record.status, "completed")
        self.assertGreaterEqual(record.item_count, 1)

        roles = [item.role for item in record.items]
        self.assertIn("main", roles)

    def test_revert_execution_marks_items_as_reverted(self) -> None:
        writer = ResolveTimelineWriter(self.mock_timeline)
        record = writer.apply_plan(self.plan, dry_run=True)
        reverted = writer.revert_execution(record)

        self.assertEqual(reverted.status, "reverted")
        for item in reverted.items:
            self.assertEqual(item.status, "reverted")


if __name__ == "__main__":
    unittest.main()
