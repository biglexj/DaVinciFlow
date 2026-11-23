"""Utilidades HTTP compartidas por los adaptadores de proveedores de IA.

Centraliza el comportamiento que el cliente de Gemini ya tenía probado (reintentos
con ``Retry-After``, límite de 30 s, tres intentos y sanitizado de credenciales en los
diagnósticos) para que los adaptadores nuevos no dupliquen esa lógica ni cambien su
semántica.
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from typing import Any, Mapping

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_ATTEMPTS = 3
RETRYABLE_STATUS = (500, 502, 503, 504)
MAX_RETRY_AFTER_SECONDS = 30.0
USER_AGENT = "DaVinciFlow/0.2.0"


def retry_delay(headers: Any, attempt: int) -> float:
    """Respeta ``Retry-After`` hasta 30 segundos; en su ausencia usa espera progresiva."""
    value = headers.get("Retry-After") if headers else None
    if value:
        try:
            return min(float(value), MAX_RETRY_AFTER_SECONDS)
        except (TypeError, ValueError):
            pass
    return 2.0 ** (attempt + 1) + random.uniform(0.0, 1.0)


def sanitize_detail(body: str, secrets: tuple[str, ...] = ()) -> str:
    """Resume el cuerpo de una respuesta de error y elimina credenciales antes de mostrarlo."""
    detail = body.strip()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict):
        for key in ("base_resp", "error", "message", "msg"):
            section = payload.get(key)
            if isinstance(section, dict):
                nested = section.get("status_msg") or section.get("message")
                if isinstance(nested, str) and nested.strip():
                    detail = nested.strip()
                    break
            elif isinstance(section, str) and section.strip():
                detail = section.strip()
                break
    for secret in secrets:
        if secret:
            detail = detail.replace(secret, "[clave oculta]")
    detail = re.sub(r"Bearer\s+[\w.\-]+", "Bearer [clave oculta]", detail)
    return " ".join(detail.split())[:800]


def post_json(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    error_type: type[Exception] = Exception,
    auth_error_type: type[Exception] | None = None,
    secrets: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Envía un POST JSON con reintentos acotados y devuelve la respuesta ya decodificada.

    Reintenta únicamente ante errores 500/502/503/504 y timeouts. Cualquier otro
    estado se propaga inmediatamente como ``error_type`` para que el llamador pueda
    distinguir un fallo de credenciales de uno de modelo; si se indica
    ``auth_error_type``, los códigos 401 y 403 se reportan con esa clase. Las
    credenciales indicadas en ``secrets`` nunca aparecen en el mensaje de error.
    """
    data = json.dumps(dict(payload)).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **dict(headers)},
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw)
        except urllib.error.HTTPError as err:
            body = ""
            try:
                body = err.read().decode("utf-8")
            except Exception:  # pragma: no cover - depende del servidor
                body = ""
            detail = sanitize_detail(body, secrets)
            if err.code in (401, 403) and auth_error_type is not None:
                raise auth_error_type(f"HTTP {err.code}: {detail}") from err
            if err.code not in RETRYABLE_STATUS or attempt == max_attempts - 1:
                raise error_type(f"HTTP {err.code}: {detail}") from err
            delay = retry_delay(err.headers, attempt)
            err.close()
            time.sleep(delay)
            last_error = err
        except TimeoutError as err:
            if attempt == max_attempts - 1:
                raise error_type(f"Tiempo de espera agotado tras {max_attempts} intentos.") from err
            time.sleep(retry_delay(None, attempt))
            last_error = err
        except urllib.error.URLError as err:
            if attempt == max_attempts - 1:
                raise error_type(f"No se pudo conectar con el servicio: {err.reason}") from err
            time.sleep(retry_delay(None, attempt))
            last_error = err

    raise error_type(f"Fallo de red persistente: {last_error}")


def extract_json_payload(text: str) -> Any:
    """Recupera el JSON de una respuesta que puede venir envuelta en texto o en vallas.

    Algunos modelos devuelven el objeto dentro de un bloque ```` ```json ```` o
    acompañado de una frase introductoria. Se eliminan las vallas y, si el texto sigue
    sin ser JSON puro, se extrae el primer objeto o arreglo balanceado.
    """
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = candidate.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(candidate)):
            char = candidate[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    fragment = candidate[start : index + 1]
                    try:
                        return json.loads(fragment)
                    except json.JSONDecodeError:
                        break
    raise ValueError("La respuesta no contiene un JSON válido.")
