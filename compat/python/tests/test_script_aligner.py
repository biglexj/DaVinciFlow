"""Pruebas unitarias para el motor de alineación con guion y corrección con IA."""

import unittest
from unittest.mock import MagicMock

from davinci_flow.ai.aligner import (
    CorrectionResult,
    ScriptAligner,
    TimelineMarker,
    apply_glossary_to_text,
)
from davinci_flow.subtitles.model import SubtitleCue


class ScriptAlignerTests(unittest.TestCase):
    """Verifica la comparación con guion, corrección de jergas/marcas y extracción de marcadores."""

    def test_apply_glossary_to_text(self) -> None:
        glossary = {"biglex": "Biglex J", "davinci": "DaVinci Resolve"}
        text = "Bienvenidos a un nuevo video con biglex usando davinci para editar."
        result, changes = apply_glossary_to_text(text, glossary)
        self.assertEqual(
            result,
            "Bienvenidos a un nuevo video con Biglex J usando DaVinci Resolve para editar.",
        )
        self.assertEqual(len(changes), 2)

    def test_local_glossary_fallback_without_client(self) -> None:
        cues = (
            SubtitleCue(text="Hola amigos de biglex", start_frame=0.0, end_frame=24.0, track_index=1),
            SubtitleCue(text="hoy veremos davinci", start_frame=25.0, end_frame=50.0, track_index=1),
        )
        aligner = ScriptAligner(client=None)
        res = aligner.align_and_correct(
            cues=cues,
            glossary={"biglex": "Biglex J", "davinci": "DaVinci Resolve"},
        )
        self.assertEqual(res.total_corrections, 2)
        self.assertEqual(res.corrected_cues[0].text, "Hola amigos de Biglex J")
        self.assertEqual(res.corrected_cues[1].text, "hoy veremos DaVinci Resolve")
        # Marcas de tiempo preservadas
        self.assertEqual(res.corrected_cues[0].start_frame, 0.0)
        self.assertEqual(res.corrected_cues[1].end_frame, 50.0)

    def test_align_and_correct_with_mocked_gemini(self) -> None:
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "aligned_cues": [
                {
                    "index": 1,
                    "corrected_text": "Bienvenidos al canal oficial de Biglex J.",
                    "changed": True,
                    "reason": "Corrección de nombre de marca y ortografía",
                },
                {
                    "index": 2,
                    "corrected_text": "Hoy vamos a automatizar subtítulos.",
                    "changed": False,
                    "reason": "Sin cambios",
                }
            ],
            "markers": [
                {
                    "frame": 0.0,
                    "color": "Cyan",
                    "name": "Introducción",
                    "note": "Bienvenida y presentación",
                },
                {
                    "frame": 25.0,
                    "color": "Yellow",
                    "name": "Tema Principal",
                    "note": "Explicación de automatización",
                }
            ],
            "summary": "2 subtítulos analizados, 1 corrección aplicada y 2 marcadores.",
        }

        cues = (
            SubtitleCue(text="bienvenidos al canal oficial de biglex", start_frame=0.0, end_frame=24.0, track_index=1),
            SubtitleCue(text="Hoy vamos a automatizar subtítulos.", start_frame=25.0, end_frame=50.0, track_index=1),
        )

        aligner = ScriptAligner(client=mock_client)
        res = aligner.align_and_correct(
            cues=cues,
            original_script="Bienvenidos al canal oficial de Biglex J. Hoy vamos a automatizar subtítulos.",
            glossary={"biglex": "Biglex J"},
            detect_markers=True,
        )

        self.assertEqual(res.total_corrections, 1)
        self.assertEqual(res.corrected_cues[0].text, "Bienvenidos al canal oficial de Biglex J.")
        self.assertEqual(res.corrected_cues[1].text, "Hoy vamos a automatizar subtítulos.")
        self.assertEqual(res.total_markers, 2)
        self.assertEqual(res.markers[0].name, "Introducción")
        self.assertEqual(res.markers[0].color, "Cyan")
        self.assertEqual(res.markers[1].color, "Yellow")

    def test_empty_cues_returns_empty_result(self) -> None:
        aligner = ScriptAligner(client=None)
        res = aligner.align_and_correct(cues=())
        self.assertEqual(res.corrected_cues, ())
        self.assertEqual(res.total_corrections, 0)
        self.assertEqual(res.total_markers, 0)


if __name__ == "__main__":
    unittest.main()
