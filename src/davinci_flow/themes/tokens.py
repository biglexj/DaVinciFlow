"""Tokens de diseño y Brand Guard para temas oficiales (Ely y Aurora)."""

from dataclasses import dataclass
from typing import Mapping

from davinci_flow.errors import DaVinciFlowError


class BrandGuardError(DaVinciFlowError):
    """Violación de la guía de estilos o uso de tokens no autorizados."""


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    """Tokens de diseño oficiales y restricciones tipográficas/cromáticas."""

    name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    context_color: str
    font_family_main: str
    font_family_context: str
    font_family_accent: str
    font_size_main: float
    font_size_context: float
    font_size_accent: float
    safe_margin_x: float = 0.05
    safe_margin_y: float = 0.08
    vertical_align: str = "bottom"  # "bottom", "center", "top"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre del tema no puede estar vacío.")
        for col_name, color in (
            ("primary_color", self.primary_color),
            ("secondary_color", self.secondary_color),
            ("accent_color", self.accent_color),
            ("text_color", self.text_color),
            ("context_color", self.context_color),
        ):
            if not color.startswith("#") or len(color) not in (7, 9):
                raise BrandGuardError(
                    f"Color '{color}' en '{col_name}' no es un código HEX válido (#RRGGBB o #RRGGBBAA)."
                )


# Registro oficial de temas permitidos
ELY_THEME = ThemeTokens(
    name="ely",
    primary_color="#06B6D4",
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
    safe_margin_x=0.05,
    safe_margin_y=0.08,
    vertical_align="bottom",
)

AURORA_THEME = ThemeTokens(
    name="aurora",
    primary_color="#F59E0B",
    secondary_color="#EF4444",
    accent_color="#EC4899",
    text_color="#FFFFFF",
    context_color="#CBD5E1",
    font_family_main="Poppins",
    font_family_context="Inter",
    font_family_accent="Poppins",
    font_size_main=0.075,
    font_size_context=0.045,
    font_size_accent=0.055,
    safe_margin_x=0.05,
    safe_margin_y=0.08,
    vertical_align="bottom",
)

THEME_REGISTRY: Mapping[str, ThemeTokens] = {
    "ely": ELY_THEME,
    "aurora": AURORA_THEME,
}


def get_theme(name: str) -> ThemeTokens:
    """Obtiene un tema oficial registrado. Lanza BrandGuardError si el tema no es oficial."""
    clean_name = name.strip().lower()
    if clean_name not in THEME_REGISTRY:
        allowed = ", ".join(sorted(THEME_REGISTRY.keys()))
        raise BrandGuardError(
            f"El tema '{name}' no está registrado en el Brand Guard. Temas oficiales disponibles: {allowed}."
        )
    return THEME_REGISTRY[clean_name]


def validate_custom_theme(tokens: ThemeTokens) -> None:
    """Comprueba que un ThemeTokens no viole las directrices de identidad de DaVinci Flow."""
    if tokens.name.lower() not in THEME_REGISTRY:
        raise BrandGuardError(f"Tema no autorizado por Brand Guard: '{tokens.name}'.")
    if tokens.font_size_main <= tokens.font_size_context:
        raise BrandGuardError("El tamaño del texto principal debe ser mayor que el texto de contexto.")
    if tokens.safe_margin_x < 0.02 or tokens.safe_margin_y < 0.02:
        raise BrandGuardError("Los márgenes seguros no pueden ser inferiores al 2% (0.02).")
