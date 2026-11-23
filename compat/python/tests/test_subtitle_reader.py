"""Pruebas del lector de subtítulos de Resolve."""

import unittest

from davinci_flow.errors import SubtitleTrackError
from davinci_flow.resolve.subtitle_reader import ResolveSubtitleReader


class FakeSubtitleItem:
    def __init__(self, text: str, start: float, end: float) -> None:
        self._text = text
        self._start = start
        self._end = end

    def GetName(self) -> str:
        return self._text

    def GetStart(self, subframe_precision: bool) -> float:
        return self._start

    def GetEnd(self, subframe_precision: bool) -> float:
        return self._end


class FakeTimeline:
    def __init__(
        self,
        subtitle_tracks: dict[int, list[FakeSubtitleItem]] | None = None,
        video_tracks: dict[int, list[FakeSubtitleItem]] | None = None,
    ) -> None:
        self._subtitle_tracks = subtitle_tracks or {}
        self._video_tracks = video_tracks or {}

    def GetTrackCount(self, track_type: str) -> int:
        if track_type == "subtitle":
            return max(self._subtitle_tracks, default=0)
        if track_type == "video":
            return max(self._video_tracks, default=0)
        return 0

    def GetItemListInTrack(self, track_type: str, track_index: int) -> list[FakeSubtitleItem]:
        if track_type == "subtitle":
            return self._subtitle_tracks.get(track_index, [])
        if track_type == "video":
            return self._video_tracks.get(track_index, [])
        return []


class ResolveSubtitleReaderTests(unittest.TestCase):
    def test_reads_cleans_and_sorts_subtitles(self) -> None:
        timeline = FakeTimeline(
            subtitle_tracks={
                1: [
                    FakeSubtitleItem(" Segundo ", 40, 60),
                    FakeSubtitleItem("Primero", 10, 30),
                    FakeSubtitleItem("   ", 70, 80),
                ]
            }
        )

        cues = ResolveSubtitleReader(timeline).read_track(1)

        self.assertEqual([cue.text for cue in cues], ["Primero", "Segundo"])
        self.assertEqual(cues[0].start_frame, 10)
        self.assertEqual(cues[1].duration_frames, 20)

    def test_reads_from_video_track(self) -> None:
        timeline = FakeTimeline(
            video_tracks={
                1: [
                    FakeSubtitleItem("Clip Video Sub", 0, 24),
                ]
            }
        )

        cues = ResolveSubtitleReader(timeline).read_track(1, track_type="video")
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Clip Video Sub")

    def test_read_auto_falls_back_to_video_track(self) -> None:
        timeline = FakeTimeline(
            subtitle_tracks={1: []},
            video_tracks={
                1: [
                    FakeSubtitleItem("Texto en Video 1", 10, 50),
                ]
            },
        )

        cues = ResolveSubtitleReader(timeline).read_auto()
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Texto en Video 1")

    def test_rejects_timeline_without_subtitle_tracks(self) -> None:
        with self.assertRaisesRegex(SubtitleTrackError, "no contiene pistas"):
            ResolveSubtitleReader(FakeTimeline({})).read_track(1)

    def test_rejects_track_outside_available_range(self) -> None:
        timeline = FakeTimeline(subtitle_tracks={1: []})

        with self.assertRaisesRegex(SubtitleTrackError, "La pista subtitle 2 no existe"):
            ResolveSubtitleReader(timeline).read_track(2)


if __name__ == "__main__":
    unittest.main()

