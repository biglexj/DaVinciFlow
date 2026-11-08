"""Cliente HTTP ligero para la API de Google Gemini utilizando la biblioteca estándar."""

import json
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    "gemini-3.8-flash",
    "gemini-3.1-pro",
    "gemini-3.0-flash",
)
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
LONG_CONTEXT_THRESHOLD = 100_000
MAX_LONG_CONTEXT_PROMPT_CHARS = 2_000_000


@dataclass(frozen=True)
class GeminiModelInfo:
    model_id: str
    input_token_limit: int | None
    output_token_limit: int | None
    supports_structured_output: bool

    @property
    def long_context(self) -> bool:
        return bool(self.input_token_limit and self.input_token_limit >= LONG_CONTEXT_THRESHOLD)


_KNOWN_LIMITS = {
    "gemini-3.5-flash-lite": (1_048_576, 65_536),
    "gemini-3.5-flash": (1_048_576, 65_536),
    "gemini-3.7-flash": (1_048_576, 65_536),
    "gemini-3.8-flash": (1_048_576, 65_536),
}


def fallback_gemini_model_info() -> tuple[GeminiModelInfo, ...]:
    """Capacidades conocidas para el catálogo sin conexión; el escaneo de cuenta las actualiza."""
    return tuple(GeminiModelInfo(model, *_KNOWN_LIMITS.get(model, (None, None)),
                                 supports_structured_output=model.startswith("gemini-3."))
                 for model in FALLBACK_MODELS)


def _retry_delay(headers: Any, attempt: int) -> float:
    """Respeta Retry-After hasta 30 segundos; en su ausencia usa espera progresiva."""
    value = headers.get("Retry-After") if headers else None
    if value:
        try:
            return max(0.0, min(30.0, float(value)))
        except (TypeError, ValueError):
            try:
                when = parsedate_to_datetime(value)
                return max(0.0, min(30.0, (when - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    return 2.0 ** (attempt + 1) + random.uniform(0.0, 1.0)


def _error_detail(body: str, api_key: str) -> str:
    """Extrae el diagnóstico JSON y elimina credenciales antes de mostrarlo."""
    try:
        error = json.loads(body).get("error", {})
        if not isinstance(error, dict):
            return ""
        detail = " — ".join(str(error[k]) for k in ("status", "message") if error.get(k))
    except (ValueError, AttributeError):
        return ""
    detail = detail.replace(api_key, "[clave oculta]") if api_key else detail
    detail = re.sub(r"AIza[\w-]+", "[clave oculta]", detail)
    return " ".join(detail.split())[:800]


def _model_info(model: dict[str, Any]) -> GeminiModelInfo | None:
    methods = model.get("supportedGenerationMethods", [])
    name = str(model.get("name", "")).replace("models/", "").strip()
    low = name.lower()
    if not name or "generateContent" not in methods or not low.startswith("gemini-3"):
        return None
    if any(part in low for part in (
        "embedding", "aqa", "imagen", "whisper", "image", "tts", "preview",
        "audio", "custom", "experimental", "live",
    )):
        return None
    known_input, known_output = _KNOWN_LIMITS.get(name, (None, None))
    try:
        input_limit = int(model.get("inputTokenLimit") or known_input or 0) or None
    except (TypeError, ValueError):
        input_limit = known_input
    try:
        output_limit = int(model.get("outputTokenLimit") or known_output or 0) or None
    except (TypeError, ValueError):
        output_limit = known_output
    # Gemini 3 text generation models used by this editor support JSON output.
    return GeminiModelInfo(name, input_limit, output_limit, True)


def list_available_gemini_model_info(
    api_key: str | None = None,
    timeout_seconds: float = 8.0,
) -> tuple[GeminiModelInfo, ...]:
    """Consulta modelos Gemini 3 disponibles y sus límites publicados por la API."""
    try:
        resolved_key = get_gemini_api_key(api_key)
    except Exception:
        return fallback_gemini_model_info()

    found: dict[str, GeminiModelInfo] = {}
    page_token = ""
    seen_tokens: set[str] = set()
    try:
        while True:
            url = API_BASE_URL
            if page_token:
                url += "?" + urllib.parse.urlencode({"pageToken": page_token})
            request = urllib.request.Request(
                url=url,
                headers={"User-Agent": "DaVinciFlow/0.2.0", "x-goog-api-key": resolved_key},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for raw in data.get("models", []):
                if isinstance(raw, dict):
                    info = _model_info(raw)
                    if info is not None:
                        found[info.model_id] = info
            next_token = str(data.get("nextPageToken") or "")
            if not next_token or next_token in seen_tokens or len(seen_tokens) >= 20:
                break
            seen_tokens.add(next_token)
            page_token = next_token
    except Exception:
        return fallback_gemini_model_info()

    if not found:
        return fallback_gemini_model_info()

    def sort_key(info: GeminiModelInfo) -> tuple[int, str]:
        low = info.model_id.lower()
        if "3.5-flash-lite" in low:
            return (0, low)
        if "3.5-flash" in low:
            return (1, low)
        if "3.7-flash" in low:
            return (2, low)
        if "3.8-flash" in low:
            return (3, low)
        if "flash" in low:
            return (4, low)
        if "pro" in low:
            return (5, low)
        return (6, low)

    return tuple(sorted(found.values(), key=sort_key))


def list_available_gemini_models(
    api_key: str | None = None,
    timeout_seconds: float = 8.0,
) -> tuple[str, ...]:
    """Compatibilidad: devuelve solo los IDs del catálogo con límites actualizados."""
    return tuple(info.model_id for info in list_available_gemini_model_info(api_key, timeout_seconds))


def known_gemini_model_info(model_id: str) -> GeminiModelInfo | None:
    """Busca los límites estáticos conocidos de un modelo compatible, si los hay."""
    return next((info for info in fallback_gemini_model_info() if info.model_id == model_id), None)


class GeminiClient:
    """Cliente para interactuar con modelos de Google Gemini con soporte de salida estructurada."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        timeout_seconds: float = 60.0,
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
                effective_config = dict(generation_config)
                # Gemini 3.x uses provider defaults for sampling; passing these values can
                # conflict with current API guidance and some stable model configurations.
                if model.lower().startswith("gemini-3"):
                    for parameter in ("temperature", "topP", "topK", "candidateCount"):
                        effective_config.pop(parameter, None)
                body["generationConfig"] = effective_config

            payload_bytes = json.dumps(body).encode("utf-8")
            request = urllib.request.Request(
                url=url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self._api_key,
                    "User-Agent": "DaVinciFlow/0.2.0",
                },
                method="POST",
            )

            try:
                for attempt in range(3):
                    try:
                        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                            response_data = json.loads(response.read().decode("utf-8"))
                        break
                    except urllib.error.HTTPError as err:
                        if err.code not in (500, 502, 503, 504) or attempt == 2:
                            raise
                        delay = _retry_delay(err.headers, attempt)
                        err.close()
                        time.sleep(delay)
                    except TimeoutError:
                        if attempt >= 1:
                            raise
                        time.sleep(_retry_delay(None, attempt))
                self.model_name = model
                break
            except urllib.error.HTTPError as err:
                err_body = ""
                try:
                    err_body = err.read().decode("utf-8")
                except Exception:
                    pass
                finally:
                    err.close()
                detail = _error_detail(err_body, self._api_key)
                diagnostic = f" Modelo: {model}." + (f" Detalle: {detail}" if detail else "")

                if err.code in (401, 403):
                    raise GeminiCredentialsError(
                        "Clave API de Gemini rechazada o permisos insuficientes (HTTP "
                        f"{err.code}). Comprueba tu clave." + diagnostic
                    ) from err
                if err.code == 429:
                    raise GeminiError(
                        "Límite de cuota o tasa de peticiones excedida en Gemini (HTTP 429). "
                        "Comprueba la cuota y los límites del proyecto." + diagnostic
                    ) from err
                if err.code == 404 and idx < len(models_to_try) - 1:
                    last_error = err
                    continue
                if err.code >= 500:
                    raise GeminiError(
                        f"La API de Gemini devolvió HTTP {err.code} tras {attempt + 1} intento(s) con el mismo modelo."
                        + diagnostic
                    ) from err
                raise GeminiError(
                    f"Error en la API de Gemini (HTTP {err.code}). Comprueba el modelo seleccionado." + diagnostic
                ) from err
            except urllib.error.URLError as err:
                raise GeminiError(
                    f"No se pudo conectar con los servidores de Google Gemini: {err.reason}"
                ) from err
            except TimeoutError as err:
                if idx < len(models_to_try) - 1:
                    last_error = err
                    continue
                raise GeminiError(
                    f"La solicitud a Google Gemini excedió el tiempo límite tras {attempt + 1} intento(s). "
                    f"Modelo: {model}."
                ) from err
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
        if first_candidate.get("finishReason") == "MAX_TOKENS":
            raise GeminiError(
                "Gemini alcanzó el límite de salida del modelo antes de terminar la tanda. "
                "El avance anterior se conserva; reduce el tamaño de la tanda y vuelve a intentarlo."
            )
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise GeminiError("La respuesta de Gemini no contiene fragmentos de texto.")

        return "".join(part.get("text", "") for part in parts)
