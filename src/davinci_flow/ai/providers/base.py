"""Contrato común de los proveedores de IA de DaVinci Flow.

El resto del producto solo debe hablar con :class:`TextProvider`. Cada proveedor
(Google Gemini, Minimax) vive en su propio adaptador y ninguno conoce al otro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from davinci_flow.ai.credentials import credential_profile

GEMINI_PROVIDER = "gemini"
MINIMAX_PROVIDER = "minimax"


@runtime_checkable
class TextProvider(Protocol):
    """Capacidades mínimas que la aplicación exige a un proveedor de texto."""

    name: str
    model_name: str

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Any:
        """Devuelve la respuesta del modelo ya decodificada como JSON."""
        ...

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
    ) -> str:
        """Devuelve la respuesta del modelo en texto plano."""
        ...

    def test_connection(self) -> bool:
        """Comprueba que la clave y el modelo responden correctamente."""
        ...


@dataclass(frozen=True)
class ProviderInfo:
    """Metadatos de un proveedor de texto para la interfaz y la fábrica."""

    name: str
    label: str
    default_model: str
    models: tuple[str, ...]
    env_var: str
    key_label: str


GEMINI_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
)

MINIMAX_MODELS = (
    "MiniMax-M3.1-Flash",
    "MiniMax-M3",
    "MiniMax-M2.7",
    "MiniMax-M2.5",
    "MiniMax-M2.1",
    "MiniMax-M2",
    "MiniMax-Text-01",
)

PROVIDERS: dict[str, ProviderInfo] = {
    GEMINI_PROVIDER: ProviderInfo(
        name=GEMINI_PROVIDER,
        label=credential_profile(GEMINI_PROVIDER).label,
        default_model=GEMINI_MODELS[0],
        models=GEMINI_MODELS,
        env_var=credential_profile(GEMINI_PROVIDER).env_var,
        key_label=credential_profile(GEMINI_PROVIDER).label,
    ),
    MINIMAX_PROVIDER: ProviderInfo(
        name=MINIMAX_PROVIDER,
        label=credential_profile(MINIMAX_PROVIDER).label,
        default_model=MINIMAX_MODELS[0],
        models=MINIMAX_MODELS,
        env_var=credential_profile(MINIMAX_PROVIDER).env_var,
        key_label=credential_profile(MINIMAX_PROVIDER).label,
    ),
}


def provider_names() -> tuple[str, ...]:
    """Nombres de los proveedores soportados, en orden estable."""
    return tuple(PROVIDERS.keys())


def provider_info(name: str) -> ProviderInfo:
    """Devuelve los metadatos de un proveedor o lanza ``KeyError`` si no existe."""
    try:
        return PROVIDERS[name]
    except KeyError as err:
        raise KeyError(
            f"Proveedor desconocido: '{name}'. Disponibles: {', '.join(provider_names())}."
        ) from err
