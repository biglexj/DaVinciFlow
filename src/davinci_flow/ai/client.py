"""Cliente HTTP ligero para la API de Google Gemini utilizando la biblioteca estándar."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from davinci_flow.ai.credentials import get_gemini_api_key
from davinci_flow.errors import GeminiCredentialsError, GeminiError

DEFAULT_MODEL = "gemini-2.5-flash"
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    """Cliente para interactuar con modelos de Google Gemini con soporte de salida estructurada."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = get_gemini_api_key(api_key)
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any]:
        """Envía una solicitud a Gemini forzando respuesta en formato JSON estructurado."""
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "temperature": max(0.0, min(1.0, temperature)),
        }

        raw_text = self._call_api(
            prompt=prompt,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as err:
            raise GeminiError(f"La respuesta de Gemini no es un JSON válido: {err}") from err

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
    ) -> str:
        """Envía una solicitud a Gemini y retorna el texto resultante."""
        generation_config: dict[str, Any] = {
            "temperature": max(0.0, min(1.0, temperature)),
        }
        return self._call_api(
            prompt=prompt,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )

    def test_connection(self) -> bool:
        """Verifica la conectividad y validez de la clave API con una consulta mínima."""
        try:
            result = self.generate_text("Responde únicamente 'OK'", temperature=0.0)
            return bool(result and "ok" in result.lower())
        except Exception:
            return False

    def _call_api(
        self,
        prompt: str,
        system_instruction: str = "",
        generation_config: dict[str, Any] | None = None,
    ) -> str:
        """Construye y despacha la petición HTTP a la API REST v1beta de Gemini."""
        url = f"{API_BASE_URL}/{self.model_name}:generateContent?key={urllib.parse.quote(self._api_key)}"

        body: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
        }

        if system_instruction and system_instruction.strip():
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction.strip()}],
            }

        if generation_config:
            body["generationConfig"] = generation_config

        payload_bytes = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DaVinciFlow/0.1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = ""
            try:
                err_body = err.read().decode("utf-8")
            except Exception:
                pass

            if err.code in (401, 403):
                raise GeminiCredentialsError(
                    "Clave API de Gemini rechazada o permisos insuficientes (HTTP "
                    f"{err.code}). Comprueba tu clave."
                ) from err
            if err.code == 429:
                raise GeminiError(
                    "Límite de cuota o tasa de peticiones excedida en Gemini (HTTP 429). "
                    "Espera unos segundos antes de reintentar."
                ) from err
            raise GeminiError(
                f"Error en la API de Gemini (HTTP {err.code}): {err.reason}. {err_body[:200]}"
            ) from err
        except urllib.error.URLError as err:
            raise GeminiError(
                f"No se pudo conectar con los servidores de Google Gemini: {err.reason}"
            ) from err
        except TimeoutError as err:
            raise GeminiError("La solicitud a Google Gemini excedió el tiempo límite de espera.") from err
        except Exception as err:
            raise GeminiError(f"Error inesperado al consultar Gemini: {err}") from err

        candidates = response_data.get("candidates", [])
        if not candidates:
            raise GeminiError("Gemini no devolvió candidatos de respuesta (posible bloqueo de seguridad).")

        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise GeminiError("La respuesta de Gemini no contiene fragmentos de texto.")

        return "".join(part.get("text", "") for part in parts)
