"""Pruebas unitarias para los argumentos de línea de comandos de davinci_flow."""

import io
import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.__main__ import main
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.reconciler import PlanDiff
from davinci_flow.generation.record import GenerationExecutionRecord
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

    def test_about_flag_prints_info_and_returns_zero(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = main(["--about"])
            self.assertEqual(result, 0)
            output = mock_stdout.getvalue()
            self.assertIn("DAVINCI FLOW", output.upper())
            self.assertIn("biglexj", output)
            self.assertIn("https://buymeacoffee.com/biglexj", output)

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
        plan = GenerationPlan(
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
        mock_plan.return_value = (plan, None)

        result = main(["--plan"])
        self.assertEqual(result, 0)
        mock_plan.assert_called_once_with(
            track_index=1,
            theme_name="ely",
            profile_name="natural",
            enable_sfx=True,
            original_script="",
            glossary={},
            api_key=None,
            model_name="gemini-3.6-flash",
            use_ai_correction=False,
            srt_path=None,
        )

    @patch("davinci_flow.__main__.generate_from_active_timeline")
    def test_generate_flag_calls_generator(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = GenerationExecutionRecord(
            execution_id="exec_1",
            plan_id="p1",
            source_hash="h1",
            project_name="Proj",
            timeline_name="TL",
            theme_name="ely",
            profile_name="natural",
            items=(),
        )
        result = main(["--generate", "--dry-run", "--no-sfx", "--correct-ai", "--add-markers"])
        self.assertEqual(result, 0)
        mock_generate.assert_called_once_with(
            track_index=1,
            theme_name="ely",
            profile_name="natural",
            enable_sfx=False,
            dry_run=True,
            original_script="",
            glossary={},
            api_key=None,
            model_name="gemini-3.6-flash",
            use_ai_correction=True,
            insert_markers=True,
            srt_path=None,
        )

    @patch("davinci_flow.__main__.plan_active_subtitles")
    def test_plan_with_script_and_glossary(self, mock_plan: MagicMock) -> None:
        cue = SubtitleCue(text="Prueba", start_frame=0.0, end_frame=24.0, track_index=1)
        block = CaptionBlock(
            id="b1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=24.0,
            original_text="Prueba",
            normalized_text="Prueba",
            main_text="Prueba",
        )
        plan = GenerationPlan(
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
        mock_plan.return_value = (plan, None)

        result = main(["--plan", "--script", "Guion de prueba", "--glossary", "marca: MiMarca", "--gemini-key", "clave123"])
        self.assertEqual(result, 0)
        mock_plan.assert_called_once_with(
            track_index=1,
            theme_name="ely",
            profile_name="natural",
            enable_sfx=True,
            original_script="Guion de prueba",
            glossary={"marca": "MiMarca"},
            api_key="clave123",
            model_name="gemini-3.6-flash",
            use_ai_correction=True,
            srt_path=None,
        )


    @patch("davinci_flow.__main__.reconcile_active_timeline")
    def test_reconcile_flag_prints_diff(self, mock_reconcile: MagicMock) -> None:
        mock_reconcile.return_value = PlanDiff(
            previous_plan_id="plan_old",
            is_identical=True,
            added_blocks=(),
            modified_blocks=(),
            deleted_block_ids=(),
            unchanged_blocks=(),
        )
        result = main(["--reconcile", "path/to/plan.json"])
        self.assertEqual(result, 0)
        mock_reconcile.assert_called_once_with("path/to/plan.json", track_index=1)


if __name__ == "__main__":
    unittest.main()
