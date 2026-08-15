"""Pruebas unitarias para los argumentos de línea de comandos de davinci_flow."""

import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.__main__ import main
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.model import SubtitleCue


class MainCliTests(unittest.TestCase):
    """Verifica el comportamiento de la CLI ante diferentes opciones y flags."""

    def test_invalid_track_returns_error_code_2(self) -> None:
        result = main(["--track", "0"])
        self.assertEqual(result, 2)

    def test_invalid_limit_returns_error_code_2(self) -> None:
        result = main(["--limit", "-1"])
        self.assertEqual(result, 2)

    @patch("davinci_flow.__main__.plan_active_subtitles")
    def test_plan_flag_prints_layers_and_returns_zero(self, mock_plan: MagicMock) -> None:
        cue = SubtitleCue(text="Prueba", start_frame=0.0, end_frame=24.0, track_index=1)
        block = CaptionBlock(
            id="b1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=24.0,
            original_text="Prueba",
            normalized_text="Prueba",
            main_text="Prueba",
            context_text="Contexto",
        )
        mock_plan.return_value = GenerationPlan(
            plan_id="plan_test",
            project_name="TestProj",
            timeline_name="TestTimeline",
            track_index=1,
            fps=24.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            theme_name="ely",
            profile_name="natural",
            source_hash="abcd1234efgh5678",
            blocks=(block,),
        )

        result = main(["--plan"])
        self.assertEqual(result, 0)
        mock_plan.assert_called_once_with(track_index=1, theme_name="ely", profile_name="natural")


if __name__ == "__main__":
    unittest.main()
