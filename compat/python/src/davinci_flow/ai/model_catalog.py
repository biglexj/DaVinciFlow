"""Capacidades de contexto publicadas para modelos editoriales compatibles."""

from dataclasses import dataclass

from davinci_flow.ai.client import (
    LONG_CONTEXT_THRESHOLD,
    MAX_LONG_CONTEXT_PROMPT_CHARS,
    GeminiModelInfo,
    fallback_gemini_model_info,
)
from davinci_flow.ai.providers.base import GEMINI_PROVIDER, MINIMAX_PROVIDER

DEFAULT_PROMPT_CHAR_LIMIT = 45_000


@dataclass(frozen=True)
class ModelCapability:
    provider: str
    model_id: str
    input_token_limit: int | None = None
    output_token_limit: int | None = None
    supports_structured_output: bool = False

    @property
    def long_context(self) -> bool:
        return bool(self.input_token_limit and self.input_token_limit >= LONG_CONTEXT_THRESHOLD)

    @property
    def context_label(self) -> str:
        if not self.input_token_limit:
            return "capacidad no verificada"
        if self.input_token_limit >= 1_000_000:
            return f"{self.input_token_limit / 1_000_000:g} M de entrada"
        return f"{self.input_token_limit:,} tokens de entrada"

    def prompt_char_limit(self, enabled: bool) -> int:
        if not enabled or not self.long_context:
            return DEFAULT_PROMPT_CHAR_LIMIT
        return min(MAX_LONG_CONTEXT_PROMPT_CHARS, self.input_token_limit * 2)


def from_gemini(info: GeminiModelInfo) -> ModelCapability:
    return ModelCapability(GEMINI_PROVIDER, info.model_id, info.input_token_limit,
                           info.output_token_limit, info.supports_structured_output)


def gemini_fallback_capabilities() -> tuple[ModelCapability, ...]:
    return tuple(from_gemini(info) for info in fallback_gemini_model_info())


def minimax_model_capabilities(model_ids: tuple[str, ...]) -> tuple[ModelCapability, ...]:
    """Marca solo modelos MiniMax con contexto largo publicado; no asume su límite de salida."""
    return tuple(
        ModelCapability(MINIMAX_PROVIDER, model_id, 1_000_000, None, True)
        if model_id.lower() in ("minimax-m3", "minimax-m3.1-flash") else
        ModelCapability(MINIMAX_PROVIDER, model_id)
        for model_id in model_ids
    )


def capability_for(provider: str, model_id: str,
                   capabilities: tuple[ModelCapability, ...] | list[ModelCapability] = ()) -> ModelCapability:
    for capability in capabilities:
        if capability.provider == provider and capability.model_id == model_id:
            return capability
    if provider == GEMINI_PROVIDER:
        return next((item for item in gemini_fallback_capabilities() if item.model_id == model_id),
                    ModelCapability(provider, model_id))
    return ModelCapability(provider, model_id, 1_000_000, None, True) if (
        provider == MINIMAX_PROVIDER
        and model_id.lower() in ("minimax-m3", "minimax-m3.1-flash")
    ) else ModelCapability(provider, model_id)
