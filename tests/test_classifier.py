"""Pruebas unitarias para el clasificador semántico de capas de subtítulos."""

import unittest

from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.classifier import (
    classify_text_layers,
    create_caption_block_from_cue,
    create_caption_blocks_from_cues,
)
from davinci_flow.subtitles.model import SubtitleCue


class SubtitleClassifierTests(unittest.TestCase):
    """Verifica la asignación determinista de capas (1, 2 y 3 capas), intenciones y razones."""

    def test_single_layer_for_short_phrases(self) -> None:
        short_texts = [
            "¡Hola a todos!",
            "Exactamente.",
            "DaVinci Flow",
            "10,000 millones",
        ]
        for text in short_texts:
            result = classify_text_layers(text)
            self.assertEqual(result.context_text, None)
            self.assertEqual(result.accent_text, None)
            self.assertTrue(len(result.main_text) > 0)
            self.assertEqual(result.confidence, 1.0)
            self.assertIn("corta o atómica", result.reason)

    def test_two_layers_with_intro_connector(self) -> None:
        text = "Por ejemplo, este algoritmo optimiza el render."
        result = classify_text_layers(text)
        self.assertIsNotNone(result.context_text)
        self.assertTrue(result.context_text.lower().startswith("por ejemplo"))
        self.assertEqual(result.main_text, "este algoritmo optimiza el render.")
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertIn("Conector introductorio", result.reason)

    def test_three_layers_with_connector_and_comma_split(self) -> None:
        text = "Sin embargo, si aplicamos esta fórmula, obtendremos diez mil millones de resultados."
        result = classify_text_layers(text)
        self.assertIsNotNone(result.context_text)
        self.assertIsNotNone(result.accent_text)
        self.assertTrue(len(result.main_text) > 0)
        self.assertTrue(result.context_text.lower().startswith("sin embargo"))
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_detects_question_intent(self) -> None:
        text = "¿Cómo podemos automatizar este flujo de trabajo?"
        result = classify_text_layers(text)
        self.assertEqual(result.intent, "question")

    def test_detects_exclamation_intent(self) -> None:
        text = "¡Esto es absolutamente increíble!"
        result = classify_text_layers(text)
        self.assertEqual(result.intent, "exclamation")

    def test_detects_negation_intent(self) -> None:
        text = "No debemos saltar ninguna validación técnica."
        result = classify_text_layers(text)
        self.assertEqual(result.intent, "negation")
        # Asegurar que la negación permanece en el texto sin perderse
        self.assertIn("No", result.normalized_text)

    def test_reconstruction_contains_all_words(self) -> None:
        text = "En primer lugar, configuremos la resolución del proyecto antes de generar."
        cue = SubtitleCue(text=text, start_frame=100.0, end_frame=200.0, track_index=1)
        block = create_caption_block_from_cue(cue, "test_block_1")

        self.assertIsInstance(block, CaptionBlock)
        self.assertEqual(block.start_frame, 100.0)
        self.assertEqual(block.end_frame, 200.0)
        self.assertEqual(block.duration_frames, 100.0)

        # Verificar que el texto reconstruido contenga las palabras clave
        for word in ["primer", "lugar", "configuremos", "resolución", "proyecto"]:
            self.assertIn(word, block.reconstructed_text.lower())

    def test_create_blocks_from_multiple_cues(self) -> None:
        cues = [
            SubtitleCue(text="Hola mundo", start_frame=0.0, end_frame=50.0, track_index=1),
            SubtitleCue(text="Por lo tanto, avanzamos con rigor.", start_frame=55.0, end_frame=120.0, track_index=1),
        ]
        blocks = create_caption_blocks_from_cues(cues)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].layer_count, 1)
        self.assertGreaterEqual(blocks[1].layer_count, 2)


if __name__ == "__main__":
    unittest.main()
