"""Pruebas unitarias para Brand Guard y tokens de temas oficiales."""

import unittest

from davinci_flow.themes.tokens import (
    AURORA_THEME,
    ELY_THEME,
    BrandGuardError,
    ThemeTokens,
    get_theme,
    validate_custom_theme,
)


class ThemesAndBrandGuardTests(unittest.TestCase):
    """Verifica que solo los temas y tokens oficiales sean admitidos."""

    def test_get_official_ely_theme(self) -> None:
        theme = get_theme("ely")
        self.assertEqual(theme.name, "ely")
        self.assertEqual(theme.primary_color, "#06B6D4")
        self.assertEqual(theme.accent_color, "#8B5CF6")
        self.assertEqual(theme.font_family_main, "Montserrat")

    def test_get_official_aurora_theme(self) -> None:
        theme = get_theme("aurora")
        self.assertEqual(theme.name, "aurora")
        self.assertEqual(theme.primary_color, "#F59E0B")
        self.assertEqual(theme.accent_color, "#EC4899")
        self.assertEqual(theme.font_family_main, "Poppins")

    def test_rejects_unauthorized_theme_name(self) -> None:
        with self.assertRaises(BrandGuardError):
            get_theme("cyberpunk_neon")

    def test_rejects_invalid_hex_colors(self) -> None:
        with self.assertRaises(BrandGuardError):
            ThemeTokens(
                name="ely",
                primary_color="blue",  # Color no HEX
                secondary_color="#3B82F6",
                accent_color="#8B5CF6",
                text_color="#FFFFFF",
                context_color="#94A3B8",
                font_family_main="Montserrat",
                font_family_context="Inter",
                font_family_accent="Montserrat",
                font_size_main=0.075,
                font_size_context=0.045,
                font_size_accent=0.055,
            )

    def test_validate_custom_theme_checks_hierarchy(self) -> None:
        # Si el tamaño principal es menor al contexto, debe fallar
        invalid_theme = ThemeTokens(
            name="ely",
            primary_color="#06B6D4",
            secondary_color="#3B82F6",
            accent_color="#8B5CF6",
            text_color="#FFFFFF",
            context_color="#94A3B8",
            font_family_main="Montserrat",
            font_family_context="Inter",
            font_family_accent="Montserrat",
            font_size_main=0.03,  # Menor que context
            font_size_context=0.05,
            font_size_accent=0.04,
        )
        with self.assertRaises(BrandGuardError):
            validate_custom_theme(invalid_theme)


if __name__ == "__main__":
    unittest.main()
