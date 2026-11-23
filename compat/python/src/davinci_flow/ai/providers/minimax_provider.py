"""Adaptador del proveedor Minimax.

Usa el endpoint oficial de chatCompletion v2 de la plataforma Minimax, con formato de
respuesta compatible con OpenAI. Reglas heredadas del cliente de Gemini que se mantienen
en este adaptador:

- No se cambia el modelo de forma silenciosa: si el modelo falla, falla la llamada.
- Se reintenta solo ante 500/502/503/504 y timeouts, con espera progresiva acotada.
- Las credenciales nunca aparecen en los mensajes de error.
"""

from __future__ import annotations

from typing import Any

from davinci_flow.ai.credentials import get_minimax_api_key
from davinci_flow.ai.http import (
    DEFAULT_TIMEOUT_SECONDS,
    extract_json_payload,
    post_json,
)
from davinci_flow.ai.providers.base import MINIMAX_MODELS, MINIMAX_PROVIDER
from davinci_flow.errors import MinimaxCredentialsError, MinimaxError

API_BASE_URL = "https://api.minimax.io/v1"
CHAT_COMPLETION_PATH = "/text/chatcompletion_v2"
DEFAULT_MINIMAX_MODEL = MINIMAX_MODELS[0]
DEFAULT_TEMPERATURE = 0.4

JSON_INSTRUCTION = (
    "Responde exclusivamente con un JSON válido y nada más: sin explicaciones, "
    "sin texto antes o después y sin bloques de código."
)


class MinimaxProvider:
    """Cliente de texto de Minimax que cumple el contrato ``TextProvider``."""

    name = MINIMAX_PROVIDER

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MINIMAX_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._api_key = get_minimax_api_key(api_key)
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Envía el prompt a Minimax y devuelve el contenido de la respuesta."""
        messages: list[dict[str, str]] = []
        if system_instruction.strip():
            messages.append({"role": "system", "content": system_instruction.strip()})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "temperature": max(0.0, min(float(temperature), 1.0)),
            "stream": False,
        }

        response = post_json(
            url=f"{self.base_url}{CHAT_COMPLETION_PATH}",
            payload=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout_seconds=self.timeout_seconds,
            error_type=MinimaxError,
            auth_error_type=MinimaxCredentialsError,
            secrets=(self._api_key,),
        )

        self._raise_for_status(response)

        choices = response.get("choices") or []
        if not choices:
            raise MinimaxError("La respuesta de Minimax no contiene ninguna alternativa de chat.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            # Algunas respuestas entregan el contenido como lista de fragmentos de texto.
            content = "".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part)
                for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise MinimaxError("La respuesta de Minimax llegó sin contenido de texto.")
        return content.strip()

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Any:
        """Pide JSON al modelo y lo decodifica tolerando vallas o texto alrededor."""
        raw = self.generate_text(
            f"{prompt}\n\n{JSON_INSTRUCTION}",
            system_instruction=system_instruction,
            temperature=temperature,
        )
        try:
            return extract_json_payload(raw)
        except ValueError as err:
            raise MinimaxError(f"La respuesta de Minimax no es un JSON válido: {err}") from err

    def test_connection(self) -> bool:
        """Verifica que la clave y el modelo responden correctamente."""
        try:
            result = self.generate_text("Responde únicamente 'OK'", temperature=0.0)
            return bool(result and "ok" in result.lower())
        except Exception:
            return False

    def _raise_for_status(self, response: dict[str, Any]) -> None:
        """Valida ``base_resp`` de Minimax, que reporta errores lógicos con HTTP 200."""
        base_resp = response.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code in (None, 0):
            return
        status_msg = str(base_resp.get("status_msg") or "error desconocido")
        raise MinimaxError(f"Minimax rechazó la solicitud (código {status_code}): {status_msg}")
