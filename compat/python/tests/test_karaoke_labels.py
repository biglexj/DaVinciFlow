import unittest

from davinci_flow.editorial.karaoke import plan_instrumental_labels
from davinci_flow.subtitles.model import SubtitleCue


class KaraokeLabelTests(unittest.TestCase):
    def test_labels_only_intro_gap_and_outro_without_covering_lyrics(self):
        cues = (SubtitleCue('Primera frase', 20, 40, 1), SubtitleCue('Segunda frase', 60, 80, 1))
        labels = plan_instrumental_labels(cues, 0, 100)
        self.assertEqual([(s.start_frame, s.end_frame) for s in labels], [(0, 20), (40, 60), (80, 100)])
        self.assertTrue(all(s.placement == 'bottom_left' and not s.animated for s in labels))

    def test_instrumental_marker_is_not_a_lyric_and_short_breath_can_be_excluded(self):
        cues = (SubtitleCue('Letra', 10, 30, 1), SubtitleCue('[Instrumental]', 30, 50, 1),
                SubtitleCue('Más letra', 50, 60, 1), SubtitleCue('Final', 62, 100, 1))
        labels = plan_instrumental_labels(cues, 0, 100, min_gap_frames=5)
        self.assertEqual([(s.start_frame, s.end_frame) for s in labels], [(0, 10), (30, 50)])

    def test_overlapping_cues_are_merged_and_clamped(self):
        cues = (SubtitleCue('A', 0, 30, 1), SubtitleCue('B', 20, 70, 1), SubtitleCue('C', 60, 110, 1))
        self.assertEqual(plan_instrumental_labels(cues, 10, 100), ())
