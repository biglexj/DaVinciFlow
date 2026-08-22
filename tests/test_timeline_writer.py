"""Pruebas de contrato para escritura física, verificación y reversión en Resolve."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

from davinci_flow.errors import TimelineWriteError
from davinci_flow.generation.plan import build_generation_plan
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.subtitles.model import SubtitleCue


class TimelineWriterTests(unittest.TestCase):
    """Verifica que un registro aplicado corresponda a un TimelineItem confirmado."""

    def setUp(self) -> None:
        self.mock_timeline = MagicMock()
        self.mock_timeline.GetTrackCount.side_effect = lambda _track_type: 1
        self.mock_timeline.GetTrackName.side_effect = lambda _track_type, _index: ""
        self.mock_timeline.GetStartFrame.return_value = 86_400
        self.mock_timeline.DeleteClips.return_value = True

        self.mock_media_pool = MagicMock()
        root_folder = MagicMock()
        root_folder.GetClipList.return_value = []
        root_folder.GetSubFolderList.return_value = []
        self.mock_media_pool.GetRootFolder.return_value = root_folder
        self.mock_media_pool.ImportMedia.return_value = [MagicMock()]

        self.created_items = []

        def append_side_effect(clip_infos):
            clip_info = clip_infos[0]
            item = MagicMock()
            track_type = "video" if clip_info["mediaType"] == 1 else "audio"
            item.GetTrackTypeAndIndex.return_value = [track_type, clip_info["trackIndex"]]
            item.GetStart.return_value = clip_info["recordFrame"]
            item.GetDuration.return_value = clip_info["endFrame"] - clip_info["startFrame"]
            item.GetUniqueId.return_value = f"native-{len(self.created_items) + 1}"
            item.ImportFusionComp.return_value = MagicMock()
            self.created_items.append(item)
            return [item]

        self.mock_media_pool.AppendToTimeline.side_effect = append_side_effect

        cue = SubtitleCue(
            text="Por lo tanto, DaVinci Flow automatiza con elegancia.",
            start_frame=0.0,
            end_frame=48.0,
            track_index=1,
        )
        self.plan = build_generation_plan(
            project_name="Proyecto",
            timeline_name="Timeline",
            cues=[cue],
            track_index=1,
            theme_name="ely",
        )
        self.track_mapping = {
            "DF_CONTEXT": 2,
            "DF_MAIN": 3,
            "DF_ACCENT": 4,
            "DF_SFX": 2,
        }

    def _writer(self, temp_root: str | Path) -> ResolveTimelineWriter:
        writer = ResolveTimelineWriter(
            self.mock_timeline,
            media_pool=self.mock_media_pool,
            asset_root=temp_root,
            temp_root=temp_root,
        )
        writer.track_manager.ensure_dedicated_tracks = MagicMock(return_value=self.track_mapping)
        return writer

    def test_track_manager_calculates_dedicated_tracks(self) -> None:
        manager = ResolveTrackManager(self.mock_timeline)
        indices = manager.get_track_indices()
        self.assertIn("DF_CONTEXT", indices)
        self.assertIn("DF_MAIN", indices)
        self.assertIn("DF_ACCENT", indices)
        self.assertIn("DF_SFX", indices)

    def test_dry_run_records_only_planned_items(self) -> None:
        writer = ResolveTimelineWriter(self.mock_timeline)
        record = writer.apply_plan(self.plan, dry_run=True)

        self.assertEqual(record.status, "dry_run")
        self.assertGreaterEqual(record.item_count, 1)
        self.assertTrue(all(item.status == "planned" for item in record.items))
        self.assertTrue(all(item.native_item_id is None for item in record.items))
        self.mock_media_pool.AppendToTimeline.assert_not_called()

    def test_real_generation_appends_exact_timeline_items_and_imports_fusion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            writer = self._writer(temp_root)
            record = writer.apply_plan(self.plan)

        self.assertEqual(record.status, "completed")
        self.assertTrue(all(item.status == "applied" for item in record.items))
        self.assertTrue(all(item.native_item_id for item in record.items))
        self.assertEqual(self.mock_media_pool.AppendToTimeline.call_count, record.item_count)

        first_clip_info = self.mock_media_pool.AppendToTimeline.call_args_list[0].args[0][0]
        self.assertEqual(first_clip_info["recordFrame"], 86_400)
        self.assertEqual(first_clip_info["endFrame"] - first_clip_info["startFrame"], 48)
        self.created_items[0].ImportFusionComp.assert_called_once()

    def test_same_plan_reuses_verified_items_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            writer = self._writer(temp_root)
            first_record = writer.apply_plan(self.plan)
            items_by_track = {}
            for record_item, native_item in zip(first_record.items, self.created_items):
                native_item.GetName.return_value = writer._native_name(
                    first_record.execution_id,
                    record_item.item_id,
                )
                items_by_track.setdefault((record_item.track_type, record_item.track_index), []).append(native_item)
            self.mock_timeline.GetItemListInTrack.side_effect = (
                lambda track_type, track_index: items_by_track.get((track_type, track_index), [])
            )
            first_append_count = self.mock_media_pool.AppendToTimeline.call_count
            second_record = writer.apply_plan(self.plan)

        self.assertEqual(second_record.item_count, first_record.item_count)
        self.assertEqual(self.mock_media_pool.AppendToTimeline.call_count, first_append_count)

    def test_failed_append_never_creates_an_applied_record(self) -> None:
        self.mock_media_pool.AppendToTimeline.return_value = []
        self.mock_media_pool.AppendToTimeline.side_effect = None
        with tempfile.TemporaryDirectory() as temp_root:
            writer = self._writer(temp_root)
            with self.assertRaises(TimelineWriteError):
                writer.apply_plan(self.plan)

    def test_real_sfx_is_imported_and_appended_as_audio(self) -> None:
        block = replace(self.plan.blocks[0], sfx_proposal="sfx_click_tech_01")
        plan_with_sfx = replace(self.plan, blocks=(block,))

        with tempfile.TemporaryDirectory() as temp_root:
            writer = self._writer(temp_root)
            record = writer.apply_plan(plan_with_sfx)

        sfx_record = next(item for item in record.items if item.role == "sfx")
        self.assertEqual(sfx_record.status, "applied")
        audio_calls = [
            call.args[0][0]
            for call in self.mock_media_pool.AppendToTimeline.call_args_list
            if call.args[0][0]["mediaType"] == 2
        ]
        self.assertEqual(len(audio_calls), 1)
        self.assertEqual(audio_calls[0]["trackIndex"], self.track_mapping["DF_SFX"])

    def test_revert_deletes_only_native_items_from_the_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            writer = self._writer(temp_root)
            record = writer.apply_plan(self.plan)

        items_by_track = {}
        for record_item, native_item in zip(record.items, self.created_items):
            items_by_track.setdefault((record_item.track_type, record_item.track_index), []).append(native_item)
        unrelated = MagicMock()
        unrelated.GetUniqueId.return_value = "unrelated"
        unrelated.GetName.return_value = "Clip de usuario"

        self.mock_timeline.GetItemListInTrack.side_effect = (
            lambda track_type, track_index: items_by_track.get((track_type, track_index), []) + [unrelated]
        )
        reverted = writer.revert_execution(record)

        self.assertEqual(reverted.status, "reverted")
        self.assertTrue(all(item.status == "reverted" for item in reverted.items))
        deleted_items = self.mock_timeline.DeleteClips.call_args.args[0]
        self.assertNotIn(unrelated, deleted_items)
        self.assertEqual(len(deleted_items), record.item_count)


if __name__ == "__main__":
    unittest.main()
