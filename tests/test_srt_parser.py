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

    def test_export_cues_to_srt_and_file(self) -> None:
        from davinci_flow.subtitles.model import SubtitleCue
        from davinci_flow.subtitles.srt_parser import export_cues_to_srt_content, export_srt_file

        cues = (
            SubtitleCue(text="Primera línea", start_frame=24.0, end_frame=48.0, track_index=1),
            SubtitleCue(text="Segunda línea", start_frame=72.0, end_frame=96.0, track_index=1),
        )
        content = export_cues_to_srt_content(cues, fps=24.0)
        self.assertIn("1\n00:00:01,000 --> 00:00:02,000\nPrimera línea", content)
        self.assertIn("2\n00:00:03,000 --> 00:00:04,000\nSegunda línea", content)

        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test_out.srt"
            res_path = export_srt_file(cues, out_file, fps=24.0)
            self.assertTrue(res_path.exists())
            self.assertEqual(res_path.read_text(encoding="utf-8"), content)

    def test_export_blocks_to_srt_content(self) -> None:
        from davinci_flow.subtitles.block import CaptionBlock
        from davinci_flow.subtitles.model import SubtitleCue
        from davinci_flow.subtitles.srt_parser import export_blocks_to_srt_content

        cue = SubtitleCue(text="En resumen, DaVinci Flow es rápido.", start_frame=0.0, end_frame=48.0, track_index=1)
        block = CaptionBlock(
            id="blk_1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=48.0,
            original_text=cue.text,
            normalized_text=cue.text,
            main_text="DaVinci Flow",
            context_text="En resumen,",
            accent_text="es rápido.",
        )
        content_combined = export_blocks_to_srt_content([block], fps=24.0, combine_layers=True)
        self.assertIn("En resumen, DaVinci Flow es rápido.", content_combined)

        content_main = export_blocks_to_srt_content([block], fps=24.0, combine_layers=False)
        self.assertIn("DaVinci Flow", content_main)
        self.assertNotIn("En resumen,", content_main)


if __name__ == "__main__":
    unittest.main()
