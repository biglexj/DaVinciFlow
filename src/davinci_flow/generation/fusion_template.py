"""Generador de plantillas Fusion (.setting) y configuración de nodos TextPlus con animaciones paramétricas."""

from typing import Tuple

from davinci_flow.themes.tokens import ThemeTokens

SUPPORTED_ANIMATION_PRESETS = (
    "none",
    "pop_bounce",
    "slide_up",
    "fade_smooth",
    "kinetic_pulse",
)


def hex_to_rgb_float(hex_color: str) -> Tuple[float, float, float]:
    """Convierte un color HEX (#RRGGBB) a una tupla de valores flotantes normalizados (0.0 a 1.0)."""
    hex_clean = hex_color.lstrip("#")
    if len(hex_clean) == 6 or len(hex_clean) == 8:
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
    animation_preset: str = "none",
) -> str:
    """Genera la estructura de un archivo Fusion .setting con un nodo TextPlus, animación opcional y MediaOut."""
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
    preset_clean = (animation_preset or "none").strip().lower()

    if preset_clean == "pop_bounce":
        return f"""{{
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
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 280, 82.5 }} }},
\t\t}},
\t\tDF_Transform_{role} = Transform {{
\t\t\tInputs = {{
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\tSize = Input {{
\t\t\t\t\tSourceOp = "DF_ScaleSpline_{role}",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Text_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 410, 82.5 }} }},
\t\t}},
\t\tDF_ScaleSpline_{role} = BezierSpline {{
\t\t\tSplineColor = {{ R = 225, G = 0, B = 225 }},
\t\t\tCtrlPts = {{
\t\t\t\t{{ 0, 0.85, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 4, 1.12, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 7, 1.00, Flags = {{ Linear = true }} }},
\t\t\t}},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{
\t\t\t\tIndex = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Transform_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 540, 82.5 }} }},
\t\t}}
\t}}
}}
"""

    if preset_clean == "slide_up":
        return f"""{{
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
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 280, 82.5 }} }},
\t\t}},
\t\tDF_Transform_{role} = Transform {{
\t\t\tInputs = {{
\t\t\t\tCenter = Input {{
\t\t\t\t\tSourceOp = "DF_CenterSpline_{role}",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tBlend = Input {{
\t\t\t\t\tSourceOp = "DF_BlendSpline_{role}",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Text_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 410, 82.5 }} }},
\t\t}},
\t\tDF_CenterSpline_{role} = BezierSpline {{
\t\t\tSplineColor = {{ R = 0, G = 225, B = 225 }},
\t\t\tCtrlPts = {{
\t\t\t\t{{ 0, 0.46, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 6, 0.50, Flags = {{ Linear = true }} }},
\t\t\t}},
\t\t}},
\t\tDF_BlendSpline_{role} = BezierSpline {{
\t\t\tSplineColor = {{ R = 225, G = 225, B = 0 }},
\t\t\tCtrlPts = {{
\t\t\t\t{{ 0, 0.0, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 5, 1.0, Flags = {{ Linear = true }} }},
\t\t\t}},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{
\t\t\t\tIndex = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Transform_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 540, 82.5 }} }},
\t\t}}
\t}}
}}
"""

    if preset_clean == "kinetic_pulse":
        return f"""{{
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
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 280, 82.5 }} }},
\t\t}},
\t\tDF_Transform_{role} = Transform {{
\t\t\tInputs = {{
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\tSize = Input {{
\t\t\t\t\tSourceOp = "DF_PulseSpline_{role}",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Text_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 410, 82.5 }} }},
\t\t}},
\t\tDF_PulseSpline_{role} = BezierSpline {{
\t\t\tSplineColor = {{ R = 255, G = 100, B = 50 }},
\t\t\tCtrlPts = {{
\t\t\t\t{{ 0, 1.22, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 5, 1.00, Flags = {{ Linear = true }} }},
\t\t\t}},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{
\t\t\t\tIndex = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Transform_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 540, 82.5 }} }},
\t\t}}
\t}}
}}
"""

    if preset_clean == "fade_smooth":
        return f"""{{
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
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 280, 82.5 }} }},
\t\t}},
\t\tDF_Transform_{role} = Transform {{
\t\t\tInputs = {{
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\tBlend = Input {{
\t\t\t\t\tSourceOp = "DF_BlendSpline_{role}",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Text_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 410, 82.5 }} }},
\t\t}},
\t\tDF_BlendSpline_{role} = BezierSpline {{
\t\t\tSplineColor = {{ R = 225, G = 225, B = 0 }},
\t\t\tCtrlPts = {{
\t\t\t\t{{ 0, 0.0, Flags = {{ Linear = true }} }},
\t\t\t\t{{ 6, 1.0, Flags = {{ Linear = true }} }},
\t\t\t}},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{
\t\t\t\tIndex = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "DF_Transform_{role}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 540, 82.5 }} }},
\t\t}}
\t}}
}}
"""

    # Por defecto: "none" (estático limpio)
    return f"""{{
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
