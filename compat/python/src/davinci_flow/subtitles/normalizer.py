"""Normalizador de texto determinista para subtítulos en español."""

import re
import unicodedata

from davinci_flow.errors import NormalizationError

# Espacios no estándar a convertir en espacio simple
_SPACE_PATTERN = re.compile(r"[\s\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+")
# Espacios superfluos antes de signos de cierre
_PUNCT_SPACES_BEFORE_CLOSING = re.compile(r"\s+([,.:;?!»\)])")
# Espacios superfluos después de signos de apertura
_PUNCT_SPACES_AFTER_OPENING = re.compile(r"([¿¡«\(])\s+")


def normalize_subtitle_text(text: str) -> str:
    """Limpia y normaliza el texto de un subtítulo conservando ortografía, puntuación y mayúsculas.

    - Conserva tildes, diéresis, eñes y caracteres propios del español.
    - Preserva signos de apertura y cierre: ¿?, ¡!, «», "", ().
    - Conserva números, cifras, fechas, porcentajes y nombres propios.
    - Elimina saltos de línea internos y colapsa espacios redundantes.
    """
    if not isinstance(text, str):
        raise NormalizationError("El texto de entrada debe ser una cadena de caracteres.")

    # Normalización Unicode NFC para evitar composición dividida de tildes
    normalized = unicodedata.normalize("NFC", text)

    # Eliminar caracteres de control invisibles (excepto espacios ya contemplados)
    cleaned_chars = [
        ch for ch in normalized
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\r", "\t")
    ]
    normalized = "".join(cleaned_chars)

    # Colapsar espacios múltiples y saltos de línea
    normalized = _SPACE_PATTERN.sub(" ", normalized).strip()

    if not normalized:
        raise NormalizationError("El texto del subtítulo quedó vacío tras la normalización.")

    # Ajustar espacios adyacentes a signos de puntuación
    normalized = _PUNCT_SPACES_BEFORE_CLOSING.sub(r"\1", normalized)
    normalized = _PUNCT_SPACES_AFTER_OPENING.sub(r"\1", normalized)

    return normalized
