"""Fábrica de proveedores de texto.

Permite que la aplicación elija proveedor y modelo sin que ningún módulo tenga que
importar a un proveedor concreto.
"""

from __future__ import annotations

from davinci_flow.ai.providers.base import (
    GEMINI_PROVIDER,
    MINIMAX_PROVIDER,
    PROVIDERS,
    ProviderInfo,
    TextProvider,
    provider_info,
    provider_names,
)
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


def default_model_for(provider: str) -> str:
    """Modelo por omisión de un proveedor."""
    return provider_info(provider).default_model


def build_text_provider(
    provider: str,
    model_name: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> TextProvider:
    """Construye el adaptador del proveedor solicitado.

    ``model_name`` vacío usa el modelo por omisión del proveedor. La clave se resuelve
    desde el argumento explícito, la variable de entorno o la configuración local.
    """
    info = provider_info(provider)
    resolved_model = (model_name or "").strip() or info.default_model

    if provider == GEMINI_PROVIDER:
        return GeminiProvider(
            api_key=api_key,
            model_name=resolved_model,
            timeout_seconds=timeout_seconds,
            strict_model=True,
        )
    if provider == MINIMAX_PROVIDER:
        return MinimaxProvider(
            api_key=api_key,
            model_name=resolved_model,
            timeout_seconds=timeout_seconds,
        )

    raise KeyError(
        f"Proveedor desconocido: '{provider}'. Disponibles: {', '.join(provider_names())}."
    )
