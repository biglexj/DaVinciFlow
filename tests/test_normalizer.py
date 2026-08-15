"""Pruebas unitarias para el normalizador de texto de subtítulos."""

import unittest

from davinci_flow.errors import NormalizationError
from davinci_flow.subtitles.normalizer import normalize_subtitle_text


class SubtitleNormalizerTests(unittest.TestCase):
    """Verifica la limpieza de texto conservando ortografía, tildes y signos."""

    def test_preserves_spanish_accents_and_special_chars(self) -> None:
        raw = "   ¡Atención!   El pingüino de Ñandú comió ciempiés en Málaga.   "
        expected = "¡Atención! El pingüino de Ñandú comió ciempiés en Málaga."
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_collapses_multiple_spaces_and_newlines(self) -> None:
        raw = "Primera línea\n\n  segunda\t\tlínea \r\n  tercera   "
        expected = "Primera línea segunda línea tercera"
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_preserves_punctuation_and_quotes(self) -> None:
        raw = '  ¿"Por qué esto funciona al 10,000%"?  '
        expected = '¿"Por qué esto funciona al 10,000%"?'
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_preserves_guillemets_and_em_dashes(self) -> None:
        raw = "  «DaVinci Flow — La solución más elegante»  "
        expected = "«DaVinci Flow — La solución más elegante»"
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_preserves_numbers_currencies_and_percentages(self) -> None:
        raw = "  El valor es de $1,500.50 o un 99.9% de precisión.  "
        expected = "El valor es de $1,500.50 o un 99.9% de precisión."
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_preserves_proper_names_and_acronyms(self) -> None:
        raw = "  NASA y Biglex desarrollaron el módulo.  "
        expected = "NASA y Biglex desarrollaron el módulo."
        self.assertEqual(normalize_subtitle_text(raw), expected)

    def test_rejects_empty_or_whitespace_only_text(self) -> None:
        with self.assertRaises(NormalizationError):
            normalize_subtitle_text("   \n\t  ")

    def test_rejects_non_string_input(self) -> None:
        with self.assertRaises(NormalizationError):
            normalize_subtitle_text(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
