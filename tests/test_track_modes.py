"""Pruebas unitarias para los modos de asignación de pistas (single, dual, triple)."""

import unittest
from unittest.mock import MagicMock

from davinci_flow.editorial.model import (
    Decision,
    EditorialError,
    EditorialOptions,
    Proposal,
    Snapshot,
    Template,
)
from davinci_flow.editorial.writer import EditorialWriter
from davinci_flow.generation.plan import build_generation_plan
from davinci_flow.resolve.timeline_writer import ResolveTimelineWriter
from davinci_flow.resolve.track_manager import ResolveTrackManager
from davinci_flow.subtitles.model import SubtitleCue


class TrackModesValidationTests(unittest.TestCase):
    """Verifica las opciones y validación del modo de pistas en el contrato editorial."""

    def test_editorial_options_accepts_valid_track_modes(self):
        for mode in ("single", "dual", "triple"):
            opts = EditorialOptions(track_mode=mode)
            opts.validate()
            self.assertEqual(opts.track_mode, mode)

    def test_editorial_options_rejects_invalid_track_mode(self):
        opts = EditorialOptions(track_mode="cuadruple")
        with self.assertRaises(EditorialError) as ctx:
            opts.validate()
        self.assertIn("Modo de pistas 'cuadruple' inválido", str(ctx.exception))

    def test_proposal_generation_plan_maps_tracks_per_mode(self):
        cue = SubtitleCue("Contexto Principal Énfasis", 0.0, 24.0, 1)
        snap = Snapshot("Proj", "TL", None, 24.0, 1920, 1080, 0, 1, (cue,))
        tmpl = Template("statement", "Statement", "installed_file", "path/to/Statement.setting")
        decision = Decision(0, "Contexto", "Principal", "Énfasis", {"context": "statement", "main": "statement", "accent": "statement"}, "Motivo")


        # Modo single
        p_single = Proposal(snap, (tmpl,), (decision,), "test-model", "1.1.0", EditorialOptions(track_mode="single"))
        plan_single = p_single.approve_all().generation_plan()
        self.assertEqual(plan_single.track_mapping["DF_CONTEXT"], "DF_MAIN")
        self.assertEqual(plan_single.track_mapping["DF_ACCENT"], "DF_MAIN")
        self.assertEqual(plan_single.track_mapping["DF_MAIN"], "DF_MAIN")

        # Modo dual
        p_dual = Proposal(snap, (tmpl,), (decision,), "test-model", "1.1.0", EditorialOptions(track_mode="dual"))
        plan_dual = p_dual.approve_all().generation_plan()
        self.assertEqual(plan_dual.track_mapping["DF_CONTEXT"], "DF_MAIN")
        self.assertEqual(plan_dual.track_mapping["DF_MAIN"], "DF_MAIN")
        self.assertEqual(plan_dual.track_mapping["DF_ACCENT"], "DF_ACCENT")

        # Modo triple
        p_triple = Proposal(snap, (tmpl,), (decision,), "test-model", "1.1.0", EditorialOptions(track_mode="triple"))
        plan_triple = p_triple.approve_all().generation_plan()
        self.assertEqual(plan_triple.track_mapping["DF_CONTEXT"], "DF_CONTEXT")
        self.assertEqual(plan_triple.track_mapping["DF_MAIN"], "DF_MAIN")
        self.assertEqual(plan_triple.track_mapping["DF_ACCENT"], "DF_ACCENT")


class TrackManagerModesTests(unittest.TestCase):
    """Verifica que ResolveTrackManager cree exclusivamente las pistas requeridas por el modo."""

    def setUp(self):
        self.mock_timeline = MagicMock()
        self.created_tracks = {"video": [], "audio": []}

        def add_track_side_effect(kind):
            self.created_tracks[kind].append("")
            return True

        def set_track_name_side_effect(kind, index, name):
            if 0 < index <= len(self.created_tracks[kind]):
                self.created_tracks[kind][index - 1] = name
                return True
            return False

        def get_track_name_side_effect(kind, index):
            if 0 < index <= len(self.created_tracks[kind]):
                return self.created_tracks[kind][index - 1]
            return ""

        self.mock_timeline.GetTrackCount.side_effect = lambda kind: len(self.created_tracks[kind])
        self.mock_timeline.AddTrack.side_effect = add_track_side_effect
        self.mock_timeline.SetTrackName.side_effect = set_track_name_side_effect
        self.mock_timeline.GetTrackName.side_effect = get_track_name_side_effect

    def test_single_mode_creates_only_main_track(self):
        manager = ResolveTrackManager(self.mock_timeline, track_mode="single")
        mapping = manager.ensure_dedicated_tracks()

        # Solo debe crear DF_BROLL, DF_MAIN y DF_SFX
        self.assertIn("DF_BROLL", mapping)
        self.assertIn("DF_MAIN", mapping)
        self.assertEqual(mapping["DF_CONTEXT"], mapping["DF_MAIN"])
        self.assertEqual(mapping["DF_ACCENT"], mapping["DF_MAIN"])

        created_video_names = self.created_tracks["video"]
        self.assertIn("DF_MAIN", created_video_names)
        self.assertNotIn("DF_CONTEXT", created_video_names)
        self.assertNotIn("DF_ACCENT", created_video_names)

    def test_dual_mode_creates_main_and_accent_tracks(self):
        manager = ResolveTrackManager(self.mock_timeline, track_mode="dual")
        mapping = manager.ensure_dedicated_tracks()

        self.assertIn("DF_BROLL", mapping)
        self.assertIn("DF_MAIN", mapping)
        self.assertIn("DF_ACCENT", mapping)
        self.assertEqual(mapping["DF_CONTEXT"], mapping["DF_MAIN"])
        self.assertNotEqual(mapping["DF_MAIN"], mapping["DF_ACCENT"])

        created_video_names = self.created_tracks["video"]
        self.assertIn("DF_MAIN", created_video_names)
        self.assertIn("DF_ACCENT", created_video_names)
        self.assertNotIn("DF_CONTEXT", created_video_names)

    def test_triple_mode_creates_all_three_text_tracks(self):
        manager = ResolveTrackManager(self.mock_timeline, track_mode="triple")
        mapping = manager.ensure_dedicated_tracks()

        created_video_names = self.created_tracks["video"]
        self.assertIn("DF_CONTEXT", created_video_names)
        self.assertIn("DF_MAIN", created_video_names)
        self.assertIn("DF_ACCENT", created_video_names)
        self.assertNotEqual(mapping["DF_CONTEXT"], mapping["DF_MAIN"])
        self.assertNotEqual(mapping["DF_MAIN"], mapping["DF_ACCENT"])


class TimelineWriterConsolidationTests(unittest.TestCase):
    """Verifica que ResolveTimelineWriter consolide capas por track_index evitando colisiones."""

    def test_single_track_consolidation_produces_single_clip_per_block(self):
        mock_timeline = MagicMock()
        mock_timeline.GetTrackCount.side_effect = lambda kind: 2 if kind == "video" else 1
        mock_timeline.GetTrackName.side_effect = lambda kind, idx: "DF_MAIN" if (kind == "video" and idx == 2) else ""
        mock_timeline.GetStartFrame.return_value = 86400
        mock_timeline.DeleteClips.return_value = True
        mock_timeline.GetItemListInTrack.return_value = []
        mock_timeline.InsertFusionTitleIntoTimeline = None

        mock_media_pool = MagicMock()
        root_folder = MagicMock()
        root_folder.GetClipList.return_value = []
        root_folder.GetSubFolderList.return_value = []
        mock_media_pool.GetRootFolder.return_value = root_folder
        mock_media_pool.ImportMedia.return_value = [MagicMock()]

        appended_clips = []

        def append_side_effect(clip_infos):
            clip_info = clip_infos[0]
            item = MagicMock()
            item.GetTrackTypeAndIndex.return_value = ["video", clip_info["trackIndex"]]
            item.GetStart.return_value = clip_info["recordFrame"]
            item.GetDuration.return_value = clip_info["endFrame"] - clip_info["startFrame"]
            item.GetUniqueId.return_value = f"native-{len(appended_clips) + 1}"
            item.ImportFusionComp.return_value = MagicMock()
            appended_clips.append(item)
            return [item]

        mock_media_pool.AppendToTimeline.side_effect = append_side_effect

        cue = SubtitleCue("Texto completo del bloque", 0.0, 48.0, 1)
        plan = build_generation_plan(
            project_name="P",
            timeline_name="T",
            cues=[cue],
            track_mapping={"DF_CONTEXT": "DF_MAIN", "DF_MAIN": "DF_MAIN", "DF_ACCENT": "DF_MAIN", "DF_SFX": "DF_SFX"},
        )
        # Asignar context, main y accent al bloque
        block = plan.blocks[0]
        from dataclasses import replace
        block = replace(block, context_text="Contexto", main_text="Principal", accent_text="Énfasis")
        plan = replace(plan, blocks=(block,))

        writer = ResolveTimelineWriter(mock_timeline, mock_media_pool)
        # Mock track manager para simular single mode donde DF_CONTEXT, DF_MAIN y DF_ACCENT comparten el índice 2
        writer.track_manager.ensure_dedicated_tracks = lambda: {
            "DF_BROLL": 1,
            "DF_MAIN": 2,
            "DF_CONTEXT": 2,
            "DF_ACCENT": 2,
            "DF_SFX": 1,
        }

        record = writer.apply_plan(plan, dry_run=False)

        # En modo single, las 3 capas se consolidan en 1 solo clip en la pista 2
        video_items = [it for it in record.items if it.track_type == "video"]
        self.assertEqual(len(video_items), 1)
        self.assertEqual(video_items[0].track_index, 2)
        self.assertEqual(video_items[0].content_text, "Contexto Principal Énfasis")
        self.assertEqual(len(appended_clips), 1)


if __name__ == "__main__":
    unittest.main()
