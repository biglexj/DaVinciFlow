"""Pruebas unitarias de la capa de efectos Fusion editables."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.errors import FusionEffectError
from davinci_flow.resolve.fusion_effects import (
    FusionEffectSpec,
    FusionEffectWriter,
    build_effect_setting,
)
from davinci_flow.themes.tokens import get_theme


class _FakeTimelineItem:
    """Elemento de línea de tiempo simulado."""

    def __init__(self, name="titulo"):
        self.name = name
        self.start = 0
        self.end = 0

    def GetName(self):
        return self.name

    def GetStart(self):
        return self.start

    def SetStart(self, value):
        self.start = value

    def SetEnd(self, value):
        self.end = value


class _FakeTimeline:
    """Línea de tiempo simulada con una pista de vídeo."""

    def __init__(self):
        self.tracks = {"video": {1: []}, "audio": {}, "subtitle": {}}
        self.inserted_titles = []
        self.deleted = []

    def GetTrackCount(self, track_type):
        return len(self.tracks.get(track_type, {}))

    def GetItemListInTrack(self, track_type, index):
        return list(self.tracks.get(track_type, {}).get(index, []))

    def InsertFusionTitleIntoTimeline(self, name):
        item = _FakeTimelineItem(name)
        self.inserted_titles.append(name)
        self.tracks.setdefault("video", {}).setdefault(1, []).append(item)
        return item

    def MoveClip(self, item, track_type, index, position):
        for items in self.tracks.get(track_type, {}).values():
            if item in items:
                items.remove(item)
        self.tracks.setdefault(track_type, {}).setdefault(index, []).append(item)

    def DeleteClips(self, items, ripple):
        self.deleted.extend(items)
        for items_list in self.tracks.get("video", {}).values():
            for item in items:
                if item in items_list:
                    items_list.remove(item)


class _FakeMediaPool:
    """Media Pool simulado que registra importaciones y anexados."""

    def __init__(self):
        self.imported = []
        self.appended = []
        self.next_item = None

    def ImportMedia(self, clip_infos):
        self.imported.append(clip_infos)
        self.next_item = object()
        return [self.next_item]

    def AppendToTimeline(self, clip_infos):
        self.appended.append(clip_infos)
        return [_FakeTimelineItem("comp")]


class _FakeProject:
    def __init__(self, media_pool):
        self._media_pool = media_pool

    def GetMediaPool(self):
        return self._media_pool


class _FakeSession:
    def __init__(self):
        self.timeline = _FakeTimeline()
        self.media_pool = _FakeMediaPool()
        self.project = _FakeProject(self.media_pool)


class BuildEffectSettingTests(unittest.TestCase):
    """Verifica el contenido de la composición Fusion generada."""

    def setUp(self) -> None:
        self.tokens = get_theme("ely")

    def test_contains_textplus_and_mediaout(self) -> None:
        setting = build_effect_setting(
            FusionEffectSpec(text="Hola mundo", animation_preset="fade_smooth"), self.tokens
        )
        self.assertIn("TextPlus", setting)
        self.assertIn("MediaOut", setting)
        self.assertIn('StyledText = Input { Value = "Hola mundo", }', setting)

    def test_escapes_quotes_in_text(self) -> None:
        setting = build_effect_setting(FusionEffectSpec(text='Di "hola"'), self.tokens)
        self.assertIn('\\"hola\\"', setting)

    def test_glow_adds_node_and_rewires_output(self) -> None:
        setting = build_effect_setting(
            FusionEffectSpec(text="Hola", animation_preset="fade_smooth", glow=0.6), self.tokens
        )
        self.assertIn("DF_Glow = Glow", setting)
        self.assertIn('SourceOp = "DF_Glow"', setting)

    def test_without_glow_output_stays_on_transform(self) -> None:
        setting = build_effect_setting(
            FusionEffectSpec(text="Hola", animation_preset="fade_smooth"), self.tokens
        )
        self.assertNotIn("DF_Glow", setting)

    def test_invalid_spec_is_rejected(self) -> None:
        with self.assertRaises(FusionEffectError):
            FusionEffectSpec(text="   ").validate()
        with self.assertRaises(FusionEffectError):
            FusionEffectSpec(text="Hola", role="otro").validate()
        with self.assertRaises(FusionEffectError):
            FusionEffectSpec(text="Hola", animation_preset="inexistente").validate()
        with self.assertRaises(FusionEffectError):
            FusionEffectSpec(text="Hola", position_x=2.0).validate()


class FusionEffectWriterTests(unittest.TestCase):
    """Verifica la inserción de composiciones y títulos nativos."""

    def setUp(self) -> None:
        self.session = _FakeSession()
        self.tmp = tempfile.TemporaryDirectory()
        self.writer = FusionEffectWriter(self.session, temp_root=Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_insert_composition_writes_imports_and_appends(self) -> None:
        result = self.writer.insert_composition(
            FusionEffectSpec(text="Hola", animation_preset="fade_smooth"),
            start_frame=48,
            duration_frames=120,
        )

        self.assertEqual(result.kind, "composicion_fusion")
        self.assertEqual(result.track_index, 1)
        self.assertTrue(Path(result.comp_path).is_file())
        self.assertEqual(len(self.session.media_pool.imported), 1)
        self.assertEqual(len(self.session.media_pool.appended), 1)
        appended = self.session.media_pool.appended[0][0]
        self.assertEqual(appended["mediaType"], 1)
        self.assertEqual(appended["recordFrame"], 48)

    def test_insert_composition_rejects_invalid_frames(self) -> None:
        with self.assertRaises(FusionEffectError):
            self.writer.insert_composition(FusionEffectSpec(text="Hola"), -1, 100)
        with self.assertRaises(FusionEffectError):
            self.writer.insert_composition(FusionEffectSpec(text="Hola"), 0, 0)

    def test_insert_native_title_uses_resolve_api(self) -> None:
        result = self.writer.insert_native_title("Text+", start_frame=24, duration_frames=96)

        self.assertEqual(result.kind, "titulo_nativo")
        self.assertEqual(self.session.timeline.inserted_titles, ["Text+"])
        item = self.session.timeline.tracks["video"][1][0]
        self.assertEqual(item.start, 24)
        self.assertEqual(item.end, 120)

    def test_insert_native_title_requires_name(self) -> None:
        with self.assertRaises(FusionEffectError):
            self.writer.insert_native_title("  ", 0, 100)

    def test_insert_native_title_without_video_tracks_is_rejected(self) -> None:
        self.session.timeline.tracks["video"] = {}
        with self.assertRaises(FusionEffectError):
            self.writer.insert_native_title("Text+", 0, 100)


if __name__ == "__main__":
    unittest.main()
