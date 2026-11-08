"""Adaptadores de proveedores de IA de DaVinci Flow.

Cada proveedor se encapsula detrás de :class:`TextProvider`; el resto de la aplicación
nunca depende de un proveedor concreto.
"""

from davinci_flow.ai.providers.base import (
    GEMINI_PROVIDER,
    MINIMAX_PROVIDER,
    PROVIDERS,
    ProviderInfo,
    TextProvider,
    provider_info,
    provider_names,
)
from davinci_flow.ai.providers.factory import build_text_provider, default_model_for
from davinci_flow.ai.providers.gemini_provider import GeminiProvider
from davinci_flow.ai.providers.minimax_provider import MinimaxProvider

__all__ = [
    "GEMINI_PROVIDER",
    "MINIMAX_PROVIDER",
    "PROVIDERS",
    "GeminiProvider",
    "MinimaxProvider",
    "ProviderInfo",
    "TextProvider",
    "build_text_provider",
    "default_model_for",
    "provider_info",
    "provider_names",
]
