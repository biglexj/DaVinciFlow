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
    def __init__(self, tracks: dict[int, list[FakeSubtitleItem]]) -> None:
        self._tracks = tracks

    def GetTrackCount(self, track_type: str) -> int:
        if track_type != "subtitle":
            return 0
        return max(self._tracks, default=0)

    def GetItemListInTrack(self, track_type: str, track_index: int) -> list[FakeSubtitleItem]:
        if track_type != "subtitle":
            return []
        return self._tracks.get(track_index, [])


class ResolveSubtitleReaderTests(unittest.TestCase):
    def test_reads_cleans_and_sorts_subtitles(self) -> None:
        timeline = FakeTimeline(
            {
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

    def test_rejects_timeline_without_subtitle_tracks(self) -> None:
        with self.assertRaisesRegex(SubtitleTrackError, "no contiene pistas"):
            ResolveSubtitleReader(FakeTimeline({})).read_track(1)

    def test_rejects_track_outside_available_range(self) -> None:
        timeline = FakeTimeline({1: []})

        with self.assertRaisesRegex(SubtitleTrackError, "La pista 2 no existe"):
            ResolveSubtitleReader(timeline).read_track(2)


if __name__ == "__main__":
    unittest.main()
