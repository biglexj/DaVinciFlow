"""Pruebas unitarias para el motor de montaje e inserción de B-Rolls (BRollWriter)."""

import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.assets.broll_catalog import BRollAsset, BRollProposal
from davinci_flow.resolve.broll_writer import (
    BRollAuditReport,
    BRollCut,
    BRollExecutionResult,
    BRollWriteError,
    BRollWriter,
)


class BRollWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_timeline = MagicMock()
        self.mock_timeline.GetTrackCount.side_effect = lambda track_type: 3
        self.mock_timeline.GetTrackName.side_effect = lambda track_type, idx: "DF_BROLL" if idx == 1 else f"V{idx}"
        self.mock_timeline.GetSetting.return_value = "24.0"
        self.mock_timeline.DeleteClips.return_value = True

        self.mock_media_pool = MagicMock()
        mock_root = MagicMock()
        mock_root.GetSubFolderList.return_value = []
        self.mock_media_pool.GetRootFolder.return_value = mock_root
        self.mock_media_pool.AddSubFolder.return_value = MagicMock()

        self.writer = BRollWriter(
            timeline=self.mock_timeline,
            media_pool=self.mock_media_pool,
            target_track_name="DF_BROLL",
            max_cut_frames=150.0,
            min_cut_frames=84.0,
        )

        self.sample_asset = BRollAsset(
            id="asset_anime_01",
            name="anohana_climax.mp4",
            file_path="D:/Videos/Anime/anohana_climax.mp4",
            asset_type="video",
            tags=("anohana", "emocion", "drama"),
        )

    def test_plan_cuts_keeps_short_proposal_intact(self) -> None:
        prop = BRollProposal(
            block_index=1,
            asset=self.sample_asset,
            start_frame=0.0,
            end_frame=120.0,  # 5 segundos a 24fps (< 150)
        )
        cuts = self.writer.plan_cuts_for_proposal(prop, timeline_fps=24.0, split_for_copyright=True)
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0].duration, 120.0)
        self.assertEqual(cuts[0].start_frame_tl, 0.0)
        self.assertEqual(cuts[0].end_frame_tl, 120.0)

    def test_plan_cuts_splits_long_proposal_for_copyright(self) -> None:
        prop = BRollProposal(
            block_index=1,
            asset=self.sample_asset,
            start_frame=0.0,
            end_frame=360.0,  # 15 segundos (supera los 150 frames)
        )
        cuts = self.writer.plan_cuts_for_proposal(prop, timeline_fps=24.0, split_for_copyright=True)
        self.assertGreater(len(cuts), 1)
        for cut in cuts:
            self.assertLessEqual(cut.duration, 150.0)
        total_duration = sum(c.duration for c in cuts)
        self.assertAlmostEqual(total_duration, 360.0)

    def test_calculate_source_duration_compensates_fps_ratio(self) -> None:
        clip_30fps = MagicMock()
        clip_30fps.GetClipProperty.return_value = "30.0"

        # 100 frames en timeline de 24fps -> 100 * (30 / 24) = 125 frames en fuente
        dur_src = self.writer.calculate_source_duration(100.0, clip_30fps, timeline_fps=24.0)
        self.assertEqual(dur_src, 125)

        clip_60fps = MagicMock()
        clip_60fps.GetClipProperty.return_value = "60.0"
        dur_src_60 = self.writer.calculate_source_duration(100.0, clip_60fps, timeline_fps=24.0)
        self.assertEqual(dur_src_60, 250)

    def test_dry_run_does_not_modify_timeline(self) -> None:
        prop = BRollProposal(
            block_index=1,
            asset=self.sample_asset,
            start_frame=0.0,
            end_frame=100.0,
        )
        result = self.writer.apply_brolls([prop], dry_run=True)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.total_cuts_inserted, 1)
        self.assertEqual(result.total_frames_covered, 100.0)
        self.mock_media_pool.AppendToTimeline.assert_not_called()

    def test_apply_brolls_executes_video_only_and_dynamic_chaining(self) -> None:
        prop1 = BRollProposal(
            block_index=1,
            asset=self.sample_asset,
            start_frame=0.0,
            end_frame=100.0,
        )
        prop2 = BRollProposal(
            block_index=2,
            asset=self.sample_asset,
            start_frame=100.0,
            end_frame=200.0,
        )

        created_items = []
        appended_payloads = []

        def mock_append(clip_infos):
            info = clip_infos[0]
            appended_payloads.append(info)
            item = MagicMock()
            rec = info["recordFrame"]
            dur = info["endFrame"] - info["startFrame"]
            item.GetStart.return_value = rec
            item.GetEnd.return_value = rec + dur
            item.GetName.return_value = "cut_clip"
            created_items.append(item)
            return [item]

        self.mock_media_pool.AppendToTimeline.side_effect = mock_append
        self.mock_media_pool.ImportMedia.return_value = [MagicMock()]
        self.mock_timeline.GetItemListInTrack.side_effect = lambda t, idx: created_items

        result = self.writer.apply_brolls([prop1, prop2], dry_run=False)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.total_cuts_inserted, 2)
        # Verificar mediaType: 1 en todas las inserciones para aislar el audio
        for payload in appended_payloads:
            self.assertEqual(payload["mediaType"], 1, "Debe ser mediaType: 1 (solo vídeo) para proteger el audio")

        # Verificar encadenamiento continuo
        self.assertEqual(appended_payloads[0]["recordFrame"], 0)
        self.assertEqual(appended_payloads[1]["recordFrame"], 100)

        # Auditoría debe reportar 0 huecos
        self.assertIsNotNone(result.audit)
        assert result.audit is not None
        self.assertTrue(result.audit.is_gapless)
        self.assertTrue(result.audit.is_copyright_compliant)

    def test_audit_detects_gap(self) -> None:
        clip1 = MagicMock()
        clip1.GetStart.return_value = 0.0
        clip1.GetEnd.return_value = 100.0
        clip1.GetName.return_value = "c1"

        # clip2 empieza en 110 (hueco de 10 fotogramas)
        clip2 = MagicMock()
        clip2.GetStart.return_value = 110.0
        clip2.GetEnd.return_value = 200.0
        clip2.GetName.return_value = "c2"

        self.mock_timeline.GetItemListInTrack.return_value = [clip1, clip2]
        audit = self.writer.audit_track(1)

        self.assertFalse(audit.is_gapless)
        self.assertEqual(len(audit.gaps), 1)
        self.assertEqual(audit.gaps[0], (100.0, 110.0, 10.0))

    def test_audit_detects_copyright_exceeding_clip(self) -> None:
        clip1 = MagicMock()
        clip1.GetStart.return_value = 0.0
        clip1.GetEnd.return_value = 250.0  # Supera los 150 frames
        clip1.GetName.return_value = "long_clip"

        self.mock_timeline.GetItemListInTrack.return_value = [clip1]
        audit = self.writer.audit_track(1)

        self.assertFalse(audit.is_copyright_compliant)
        self.assertEqual(len(audit.clips_exceeding_copyright), 1)
        self.assertEqual(audit.clips_exceeding_copyright[0][0], "long_clip")

    def test_clean_target_track_calls_delete_clips(self) -> None:
        c1, c2 = MagicMock(), MagicMock()
        self.mock_timeline.GetItemListInTrack.return_value = [c1, c2]

        deleted_count = self.writer.clean_target_track(1)
        self.assertEqual(deleted_count, 2)
        self.mock_timeline.DeleteClips.assert_called_once_with([c1, c2], False)


if __name__ == "__main__":
    unittest.main()
