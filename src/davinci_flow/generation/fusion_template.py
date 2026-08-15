"""Generador de plantillas Fusion (.setting) y configuración de nodos TextPlus."""

from typing import Tuple

from davinci_flow.themes.tokens import ThemeTokens


def hex_to_rgb_float(hex_color: str) -> Tuple[float, float, float]:
    """Convierte un color HEX (#RRGGBB) a una tupla de valores flotantes normalizados (0.0 a 1.0)."""
    hex_clean = hex_color.lstrip("#")
    if len(hex_clean) == 6:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        return (round(r, 4), round(g, 4), round(b, 4))
    if len(hex_clean) == 8:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        return (round(r, 4), round(g, 4), round(b, 4))
    raise ValueError(f"Formato hexadecimal inválido: '{hex_color}'")


def generate_textplus_fusion_setting(
    text: str,
    tokens: ThemeTokens,
    role: str = "main",
    pos_x: float = 0.5,
    pos_y: float = 0.15,
) -> str:
    """Genera la estructura de un archivo Fusion .setting con un nodo TextPlus y MediaOut."""
    if role == "context":
        font = tokens.font_family_context
        size = tokens.font_size_context
        r, g, b = hex_to_rgb_float(tokens.context_color)
    elif role == "accent":
        font = tokens.font_family_accent
        size = tokens.font_size_accent
        r, g, b = hex_to_rgb_float(tokens.accent_color)
    else:  # main
        font = tokens.font_family_main
        size = tokens.font_size_main
        r, g, b = hex_to_rgb_float(tokens.primary_color)

    # Escapar comillas dobles y caracteres especiales en Lua
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    return f"""{{"
\tTools = ordered() {{
\t\tDF_Text_{role} = TextPlus {{
\t\t\tInputs = {{
\t\t\t\tGlobalWidth = Input {{ Value = 1920, }},
\t\t\t\tGlobalHeight = Input {{ Value = 1080, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\tCenter = Input {{ Value = {{ {pos_x:.4f}, {pos_y:.4f} }}, }},
\t\t\t\tStyledText = Input {{ Value = "{safe_text}", }},
\t\t\t\tFont = Input {{ Value = "{font}", }},
\t\t\t\tStyle = Input {{ Value = "Bold", }},
\t\t\t\tSize = Input {{ Value = {size:.4f}, }},
\t\t\t\tRed1 = Input {{ Value = {r:.4f}, }},
\t\t\t\tGreen1 = Input {{ Value = {g:.4f}, }},
\t\t\t\tBlue1 = Input {{ Value = {b:.4f}, }},
\t\t\t\tAlpha1 = Input {{ Value = 1.0, }},
\t\t\t\tVerticalJustificationNew = Input {{ Value = 3, }},
\t\t\t\tHorizontalJustificationNew = Input {{ Value = 3, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 330, 82.5 }} }},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{
\t\t\t\tIndex = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Text_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 495, 82.5 }} }},
\t\t}}
\t}}
}}
"""
