"""Pruebas unitarias del escritor de subtítulos nativos."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.resolve.subtitle_writer import (
    SubtitleTrackWriter,
    build_srt,
    format_srt_timestamp,
    write_srt,
)
from davinci_flow.subtitles.model import SubtitleCue


def _cue(text, start=0, end=48, track=1):
    return SubtitleCue(text=text, start_frame=start, end_frame=end, track_index=track)


class SrtFormatTests(unittest.TestCase):
    """Verifica la conversión a marcas de tiempo SRT."""

    def test_format_timestamp(self) -> None:
        self.assertEqual(format_srt_timestamp(0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(1.5), "00:00:01,500")
        self.assertEqual(format_srt_timestamp(3661.25), "01:01:01,250")

    def test_negative_time_is_rejected(self) -> None:
        with self.assertRaises(SubtitleTrackError):
            format_srt_timestamp(-1)

    def test_build_srt_lists_cues_in_order(self) -> None:
        content = build_srt([_cue("Hola", 0, 48), _cue("Adiós", 48, 96)], frame_rate=24)
        self.assertIn("1\n00:00:00,000 --> 00:00:02,000\nHola", content)
        self.assertIn("2\n00:00:02,000 --> 00:00:04,000\nAdiós", content)

    def test_build_srt_requires_cues(self) -> None:
        with self.assertRaises(SubtitleTrackError):
            build_srt([], frame_rate=24)

    def test_write_srt_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_srt([_cue("Hola")], Path(tmp_dir) / "sub.srt", frame_rate=24)
            self.assertTrue(path.is_file())
            self.assertIn("Hola", path.read_text(encoding="utf-8"))


class _FakeTimeline:
    """Línea de tiempo simulada con pista de subtítulos."""

    def __init__(self):
        self.subtitle_tracks = {1: []}
        self.deleted = []

    def GetTrackCount(self, track_type):
        return len(self.subtitle_tracks) if track_type == "subtitle" else 0

    def GetItemListInTrack(self, track_type, index):
        return list(self.subtitle_tracks.get(index, []))

    def AddTrack(self, track_type, sub_track_type=None):
        self.subtitle_tracks[2] = []
        return True

    def DeleteClips(self, items, ripple):
        self.deleted.extend(items)


class _FakeMediaPool:
    """Media Pool simulado: acepta solo el ``mediaType`` configurado.

    Cuando acepta el elemento, lo coloca realmente en la pista de subtítulos, para
    que la verificación del escritor se comporte como en Resolve.
    """

    def __init__(self, timeline, accepted_media_type=2):
        self.timeline = timeline
        self.accepted_media_type = accepted_media_type
        self.imported = []
        self.appended = []

    def ImportMedia(self, clip_infos):
        self.imported.append(clip_infos)
        return [object()]

    def AppendToTimeline(self, clip_infos):
        self.appended.append(clip_infos)
        media_type = clip_infos[0].get("mediaType")
        if media_type != self.accepted_media_type:
            return []
        item = object()
        track_index = clip_infos[0].get("trackIndex", 1)
        self.timeline.subtitle_tracks.setdefault(track_index, []).append(item)
        return [item]


class _FakeProject:
    def __init__(self, media_pool):
        self._media_pool = media_pool

    def GetMediaPool(self):
        return self._media_pool


class _FakeSession:
    def __init__(self, accepted_media_type=2):
        self.timeline = _FakeTimeline()
        self.media_pool = _FakeMediaPool(self.timeline, accepted_media_type)
        self.project = _FakeProject(self.media_pool)


class SubtitleTrackWriterTests(unittest.TestCase):
    """Verifica la escritura en la pista nativa y la verificación del resultado."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _writer(self, accepted_media_type=2):
        session = _FakeSession(accepted_media_type)
        return session, SubtitleTrackWriter(session, temp_root=Path(self.tmp.name))

    def test_write_appends_to_subtitle_track(self) -> None:
        session, writer = self._writer()
        result = writer.write([_cue("Hola", 0, 48), _cue("Adiós", 48, 96)])

        self.assertTrue(result.confirmed)
        self.assertEqual(result.cue_count, 2)
        self.assertEqual(result.track_index, 1)
        self.assertTrue(Path(result.srt_path).is_file())
        self.assertEqual(len(session.media_pool.appended), 1)
        self.assertEqual(len(session.timeline.subtitle_tracks[1]), 1)

    def test_write_uses_alternative_media_type_when_needed(self) -> None:
        session, writer = self._writer(accepted_media_type=1)
        result = writer.write([_cue("Hola", 0, 48)])

        self.assertTrue(result.confirmed)
        self.assertEqual(result.method, "mediaType=1")
        self.assertEqual(len(session.media_pool.appended), 2)

    def test_write_reports_srt_path_when_resolve_refuses(self) -> None:
        _, writer = self._writer(accepted_media_type=99)
        with self.assertRaises(SubtitleTrackError) as context:
            writer.write([_cue("Hola", 0, 48)])
        self.assertIn(".srt", str(context.exception))

    def test_write_requires_cues(self) -> None:
        _, writer = self._writer()
        with self.assertRaises(SubtitleTrackError):
            writer.write([])

    def test_ensure_track_creates_missing_track(self) -> None:
        session, writer = self._writer()
        session.timeline.subtitle_tracks = {}
        self.assertEqual(writer.ensure_track(), 1)
        self.assertIn(2, session.timeline.subtitle_tracks)

    def test_frame_rate_falls_back_to_default(self) -> None:
        _, writer = self._writer()
        self.assertEqual(writer.frame_rate(), 24.0)


if __name__ == "__main__":
    unittest.main()
