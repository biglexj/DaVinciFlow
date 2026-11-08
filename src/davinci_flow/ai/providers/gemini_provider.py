"""Adaptador del proveedor Google Gemini.

No reimplementa nada: delega en :class:`davinci_flow.ai.client.GeminiClient` para
conservar exactamente su comportamiento (reintentos, errores y modelo estricto).
"""

from __future__ import annotations

from typing import Any

from davinci_flow.ai.client import DEFAULT_MODEL, GeminiClient
from davinci_flow.ai.providers.base import GEMINI_PROVIDER


class GeminiProvider:
    """Envoltorio de :class:`GeminiClient` que cumple el contrato ``TextProvider``."""

    name = GEMINI_PROVIDER

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        timeout_seconds: float = 60.0,
        strict_model: bool = True,
    ) -> None:
        self._client = GeminiClient(
            api_key=api_key,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            strict_model=strict_model,
        )

    @property
    def model_name(self) -> str:
        return self._client.model_name

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Any:
        return self._client.generate_json(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
    ) -> str:
        return self._client.generate_text(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def test_connection(self) -> bool:
        return self._client.test_connection()
