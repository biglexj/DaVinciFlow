"""Pruebas unitarias para el parseo y conversión de subtítulos SRT."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.subtitles.srt_parser import (
    SrtParseError,
    frames_to_srt_timecode,
    load_srt_file,
    parse_srt_content,
    timecode_to_frames,
)


class SrtParserTests(unittest.TestCase):
    """Verifica la conversión precisa de códigos de tiempo y parseo de bloques SRT."""

    def test_timecode_to_frames(self) -> None:
        # 1 segundo a 24fps = 24 fotogramas
        frames = timecode_to_frames("00:00:01,000", fps=24.0)
        self.assertEqual(frames, 24.0)

        # Con punto
        frames_dot = timecode_to_frames("00:00:02.500", fps=24.0)
        self.assertEqual(frames_dot, 60.0)

        # 1 hora
        frames_1h = timecode_to_frames("01:00:00,000", fps=24.0)
        self.assertEqual(frames_1h, 86400.0)

    def test_frames_to_srt_timecode(self) -> None:
        tc = frames_to_srt_timecode(24.0, fps=24.0)
        self.assertEqual(tc, "00:00:01,000")

        tc_half = frames_to_srt_timecode(60.0, fps=24.0)
        self.assertEqual(tc_half, "00:00:02,500")

    def test_invalid_timecode_raises_error(self) -> None:
        with self.assertRaises(SrtParseError):
            timecode_to_frames("tiempo_invalido")

    def test_parse_srt_content_multiline(self) -> None:
        srt_text = """
1
00:00:01,000 --> 00:00:03,500
Bienvenidos a <i>DaVinci Flow</i>.

2
00:00:04,000 --> 00:00:06,000
Automatización de subtítulos
dinámicos y multicapa.
"""
        cues = parse_srt_content(srt_text, fps=24.0, track_index=1)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text, "Bienvenidos a DaVinci Flow.")
        self.assertEqual(cues[0].start_frame, 24.0)
        self.assertEqual(cues[0].end_frame, 84.0)

        self.assertEqual(cues[1].text, "Automatización de subtítulos dinámicos y multicapa.")
        self.assertEqual(cues[1].start_frame, 96.0)
        self.assertEqual(cues[1].end_frame, 144.0)

    def test_load_srt_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write("1\n00:00:00,500 --> 00:00:02,000\nPrueba desde archivo\n")
            temp_path = f.name

        try:
            cues = load_srt_file(temp_path, fps=30.0)
            self.assertEqual(len(cues), 1)
            self.assertEqual(cues[0].text, "Prueba desde archivo")
            self.assertEqual(cues[0].start_frame, 15.0)
            self.assertEqual(cues[0].end_frame, 60.0)
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
