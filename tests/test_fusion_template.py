"""Pruebas unitarias para generador de plantillas Fusion .setting."""

import unittest

from davinci_flow.generation.fusion_template import (
    generate_textplus_fusion_setting,
    hex_to_rgb_float,
)
from davinci_flow.themes.tokens import ELY_THEME


class FusionTemplateTests(unittest.TestCase):
    """Verifica la generación sintáctica de .setting y conversión de color."""

    def test_hex_to_rgb_float(self) -> None:
        # #FFFFFF -> (1.0, 1.0, 1.0)
        self.assertEqual(hex_to_rgb_float("#FFFFFF"), (1.0, 1.0, 1.0))
        # #000000 -> (0.0, 0.0, 0.0)
        self.assertEqual(hex_to_rgb_float("#000000"), (0.0, 0.0, 0.0))

    def test_generate_textplus_fusion_setting_contains_required_nodes(self) -> None:
        setting_text = generate_textplus_fusion_setting(
            text='Hola "Mundo"',
            tokens=ELY_THEME,
            role="main",
            pos_x=0.5,
            pos_y=0.15,
        )
        self.assertIn("Tools = ordered()", setting_text)
        self.assertIn("DF_Text_main = TextPlus", setting_text)
        self.assertIn("MediaOut1 = MediaOut", setting_text)
        self.assertIn('StyledText = Input { Value = "Hola \\"Mundo\\"", }', setting_text)
        self.assertIn(f'Font = Input {{ Value = "{ELY_THEME.font_family_main}", }}', setting_text)


if __name__ == "__main__":
    unittest.main()
