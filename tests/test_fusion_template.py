"""Pruebas unitarias para generador de plantillas Fusion .setting y animaciones paramétricas."""

import unittest

from davinci_flow.generation.fusion_template import (
    SUPPORTED_ANIMATION_PRESETS,
    generate_textplus_fusion_setting,
    hex_to_rgb_float,
)
from davinci_flow.themes.tokens import ELY_THEME


class FusionTemplateTests(unittest.TestCase):
    """Verifica la generación sintáctica de .setting, conversión de color y presets de animación."""

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
            animation_preset="none",
        )
        self.assertIn("Tools = ordered()", setting_text)
        self.assertIn("DF_Text_main = TextPlus", setting_text)
        self.assertIn("MediaOut1 = MediaOut", setting_text)
        self.assertIn('StyledText = Input { Value = "Hola \\"Mundo\\"", }', setting_text)
        self.assertIn(f'Font = Input {{ Value = "{ELY_THEME.font_family_main}", }}', setting_text)

    def test_generate_pop_bounce_animation_setting(self) -> None:
        setting = generate_textplus_fusion_setting(
            text="Dinámico",
            tokens=ELY_THEME,
            role="accent",
            animation_preset="pop_bounce",
        )
        self.assertIn("DF_Transform_accent = Transform", setting)
        self.assertIn("DF_ScaleSpline_accent = BezierSpline", setting)
        self.assertIn("MediaOut1", setting)

    def test_generate_slide_up_animation_setting(self) -> None:
        setting = generate_textplus_fusion_setting(
            text="Contexto suave",
            tokens=ELY_THEME,
            role="context",
            animation_preset="slide_up",
        )
        self.assertIn("DF_Transform_context = Transform", setting)
        self.assertIn("DF_CenterSpline_context = BezierSpline", setting)
        self.assertIn("DF_BlendSpline_context = BezierSpline", setting)

    def test_generate_kinetic_pulse_and_fade_smooth(self) -> None:
        pulse = generate_textplus_fusion_setting(
            text="Impacto",
            tokens=ELY_THEME,
            role="accent",
            animation_preset="kinetic_pulse",
        )
        self.assertIn("DF_PulseSpline_accent = BezierSpline", pulse)

        fade = generate_textplus_fusion_setting(
            text="Lectura fluida",
            tokens=ELY_THEME,
            role="main",
            animation_preset="fade_smooth",
        )
        self.assertIn("DF_BlendSpline_main = BezierSpline", fade)

    def test_generate_typewriter_animation(self) -> None:
        tw = generate_textplus_fusion_setting(
            text="Escribiendo palabra a palabra",
            tokens=ELY_THEME,
            role="main",
            animation_preset="typewriter",
        )
        self.assertIn("ManualWriteOn = Input { Value = 1, }", tw)
        self.assertIn("WriteOnEnd = Input {", tw)
        self.assertIn("DF_WriteOnSpline_main = BezierSpline", tw)
        self.assertIn("MediaOut1", tw)


if __name__ == "__main__":
    unittest.main()
