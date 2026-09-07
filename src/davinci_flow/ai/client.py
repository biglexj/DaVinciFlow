"""Cliente HTTP ligero para la API de Google Gemini utilizando la biblioteca estándar."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from davinci_flow.ai.credentials import get_gemini_api_key
from davinci_flow.errors import GeminiCredentialsError, GeminiError

DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.1-pro",
    "gemini-3.0-flash",
)
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def list_available_gemini_models(
    api_key: str | None = None,
    timeout_seconds: float = 8.0,
) -> tuple[str, ...]:
    """Consulta dinámicamente los modelos disponibles en la API de Gemini que soportan generación de contenido (Gemini 3+)."""
    try:
        resolved_key = get_gemini_api_key(api_key)
    except Exception:
        return FALLBACK_MODELS

    url = API_BASE_URL
    request = urllib.request.Request(
        url=url,
        headers={"User-Agent": "DaVinciFlow/0.2.0", "x-goog-api-key": resolved_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_models = data.get("models", [])
            valid_models: list[str] = []
            for m in raw_models:
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = m.get("name", "").replace("models/", "").strip()
                    n_low = name.lower()
                    # Requerir estrictamente modelos de generación Gemini 3+ (gemini-3.x)
                    if (
                        name
                        and n_low.startswith("gemini-3")
                        and not any(
                            p in n_low for p in (
                                "embedding", "aqa", "imagen", "text-embedding", "whisper",
                                "image", "tts", "preview", "audio", "custom", "experimental",
                            )
                        )
                    ):
                        valid_models.append(name)
            if valid_models:
                def _sort_key(n: str) -> tuple[int, str]:
                    n_low = n.lower()
                    if "3.5-flash-lite" in n_low:
                        return (0, n_low)
                    if "3.5-flash" in n_low:
                        return (1, n_low)
                    if "3.7-flash" in n_low:
                        return (2, n_low)
                    if "flash" in n_low:
                        return (3, n_low)
                    if "pro" in n_low:
                        return (4, n_low)
                    return (5, n_low)

                seen: set[str] = set()
                deduped: list[str] = []
                for v in sorted(valid_models, key=_sort_key):
                    if v not in seen:
                        seen.add(v)
                        deduped.append(v)
                return tuple(deduped) if deduped else FALLBACK_MODELS
    except Exception:
        pass
    return FALLBACK_MODELS


class GeminiClient:
    """Cliente para interactuar con modelos de Google Gemini con soporte de salida estructurada."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        timeout_seconds: float = 30.0,
        strict_model: bool = False,
    ) -> None:
        self._api_key = get_gemini_api_key(api_key)
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.strict_model = strict_model

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
        """Construye y despacha la petición HTTP a la API REST v1beta de Gemini con soporte de respaldo de modelo."""
        models_to_try = [self.model_name]
        if not self.strict_model:
            models_to_try += [m for m in FALLBACK_MODELS if m != self.model_name]
        last_error: Exception | None = None

        for idx, model in enumerate(models_to_try):
            url = f"{API_BASE_URL}/{urllib.parse.quote(model, safe='')}:generateContent"

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
                    "x-goog-api-key": self._api_key,
                    "User-Agent": "DaVinciFlow/0.1.0",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                    self.model_name = model
                    break
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
                if err.code == 404 and idx < len(models_to_try) - 1:
                    last_error = err
                    continue
                if err.code >= 500:
                    raise GeminiError(f"Gemini no está disponible temporalmente (HTTP {err.code}). Reintenta con el mismo modelo.") from err
                raise GeminiError(
                    f"Error en la API de Gemini (HTTP {err.code}). Comprueba el modelo seleccionado."
                ) from err
            except urllib.error.URLError as err:
                raise GeminiError(
                    f"No se pudo conectar con los servidores de Google Gemini: {err.reason}"
                ) from err
            except TimeoutError as err:
                if idx < len(models_to_try) - 1:
                    last_error = err
                    continue
                raise GeminiError("La solicitud a Google Gemini excedió el tiempo límite de espera.") from err
            except Exception as err:
                raise GeminiError("Error inesperado al consultar Gemini.") from err
        else:
            if last_error is not None:
                raise GeminiError(f"Error en la API de Gemini: {last_error}") from last_error
            raise GeminiError("No se pudo conectar con ningún modelo compatible de Gemini.")

        candidates = response_data.get("candidates", [])
        if not candidates:
            raise GeminiError("Gemini no devolvió candidatos de respuesta (posible bloqueo de seguridad).")

        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise GeminiError("La respuesta de Gemini no contiene fragmentos de texto.")

        return "".join(part.get("text", "") for part in parts)
