"""Pruebas unitarias de integración de alto nivel para IA y marcadores en application.py."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from davinci_flow.ai.aligner import CorrectionResult, TimelineMarker
from davinci_flow.application import (
    align_and_correct_subtitles,
    generate_from_active_timeline,
    insert_ai_timeline_markers,
    plan_active_subtitles,
)
from davinci_flow.errors import ResolveConnectionError, TimelineWriteError
from davinci_flow.subtitles.model import SubtitleCue


class ApplicationAiTests(unittest.TestCase):
    """Verifica los flujos orquestados de aplicación para Gemini, guion y marcadores."""

    @patch("davinci_flow.application.connect_to_resolve")
    @patch("davinci_flow.application.ResolveSubtitleReader")
    @patch("davinci_flow.application.ScriptAligner")
    def test_align_and_correct_subtitles_flow(
        self,
        mock_aligner_cls: MagicMock,
        mock_reader_cls: MagicMock,
        mock_connect: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_connect.return_value = mock_session

        cues = (SubtitleCue(text="hola biglex", start_frame=0.0, end_frame=24.0, track_index=1),)
        mock_reader_cls.return_value.read_track.return_value = cues

        mock_aligner = MagicMock()
        mock_aligner_cls.return_value = mock_aligner
        expected_res = CorrectionResult(
            corrected_cues=(SubtitleCue(text="Hola Biglex J", start_frame=0.0, end_frame=24.0, track_index=1),),
            corrections=(),
            markers=(),
            summary="OK",
        )
        mock_aligner.align_and_correct.return_value = expected_res

        res = align_and_correct_subtitles(
            track_index=1,
            original_script="Hola Biglex J",
            glossary={"biglex": "Biglex J"},
            api_key="test-key",
        )

        self.assertEqual(res, expected_res)
        mock_aligner.align_and_correct.assert_called_once_with(
            cues=cues,
            original_script="Hola Biglex J",
            glossary={"biglex": "Biglex J"},
            detect_markers=True,
        )

    @patch("davinci_flow.application.connect_to_resolve")
    @patch("davinci_flow.application.ResolveMarkerWriter")
    def test_insert_ai_timeline_markers_flow(
        self,
        mock_writer_cls: MagicMock,
        mock_connect: MagicMock,
    ) -> None:
        mock_session = MagicMock()
        mock_connect.return_value = mock_session
        mock_writer = MagicMock()
        mock_writer.apply_markers.return_value = 3
        mock_writer_cls.return_value = mock_writer

        markers = [
            TimelineMarker(frame=0.0, color="Cyan", name="Intro"),
            TimelineMarker(frame=50.0, color="Yellow", name="Tema"),
            TimelineMarker(frame=100.0, color="Pink", name="Cierre"),
        ]

        applied = insert_ai_timeline_markers(markers, clear_existing_color=True)
        self.assertEqual(applied, 3)
        mock_writer.apply_markers.assert_called_once_with(markers, clear_existing_color=True)

    @patch("davinci_flow.application.connect_to_resolve")
    def test_dry_run_with_srt_does_not_require_resolve_session(self, mock_connect: MagicMock) -> None:
        mock_connect.side_effect = ResolveConnectionError("Sin sesión")
        srt_path = tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False, encoding="utf-8"
        )
        try:
            srt_path.write(
                "1\n00:00:00,200 --> 00:00:03,600\nHola a todo el mundo\n"
            )
            srt_path.close()
            record = generate_from_active_timeline(dry_run=True, srt_path=srt_path.name)
        finally:
            Path(srt_path.name).unlink(missing_ok=True)

        self.assertEqual(record.status, "dry_run")
        self.assertTrue(record.items)
        self.assertTrue(all(item.status == "planned" for item in record.items))

    @patch("davinci_flow.application.connect_to_resolve")
    def test_generate_without_srt_still_requires_resolve_session(self, mock_connect: MagicMock) -> None:
        mock_connect.side_effect = ResolveConnectionError("No hay sesión")
        with self.assertRaises(ResolveConnectionError):
            generate_from_active_timeline(dry_run=True, srt_path=None)


if __name__ == "__main__":
    unittest.main()
