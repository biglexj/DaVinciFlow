"""Cliente de la API de decisiones de Google Gemini (`gemini-decision-1`).

La API de decisiones no genera texto: evalúa preguntas tipadas (`noul`,
`choice`, `score`) sobre una entrada compartida y devuelve decisiones
calibradas con su probabilidad. Por eso vive aparte de
:class:`davinci_flow.ai.client.GeminiClient` y no implementa el contrato
`TextProvider`: su salida son probabilidades, no JSON.

Endpoint oficial: `POST https://generativelanguage.googleapis.com/v1beta/decisions`.
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from davinci_flow.ai.credentials import get_gemini_api_key
from davinci_flow.errors import GeminiCredentialsError, GeminiError

DECISIONS_API_URL = "https://generativelanguage.googleapis.com/v1beta/decisions"
DECISION_MODEL = "gemini-decision-1"
QUESTION_TYPES = ("noul", "choice", "score")
_MAX_QUESTIONS = 1000
_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


@dataclass(frozen=True)
class DecisionAnswer:
    """Respuesta calibrada a una pregunta de la API de decisiones."""

    key: str
    type: str
    noul: float | None = None
    choice: str | None = None
    score: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    legend: dict[str, str] = field(default_factory=dict)

    @property
    def probability(self) -> float:
        """Probabilidad de la opción ganadora, o la de «sí» en preguntas `noul`."""
        if self.type == "noul":
            return float(self.noul or 0.0)
        if self.type == "choice" and self.choice:
            return float(self.probabilities.get(self.choice, self.confidence))
        return float(self.confidence)


@dataclass(frozen=True)
class DecisionUsage:
    """Consumo de la petición: la API de decisiones no factura tokens de salida."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class DecisionClient:
    """Cliente HTTP de la API de decisiones de Gemini.

    No escribe nada en DaVinci Resolve ni en el sistema: solo consulta el
    servicio y devuelve decisiones calibradas.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DECISION_MODEL,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = get_gemini_api_key(api_key)
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.usage = DecisionUsage()

    def decide(
        self,
        input_text: str,
        questions: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, DecisionAnswer], DecisionUsage]:
        """Evalúa las preguntas sobre la entrada compartida.

        `questions` admite hasta 1.000 entradas con la forma
        `{"clave": {"type": "noul|choice|score", "instructions": "...", "criteria": {...}}}`.
        """
        if not isinstance(input_text, str) or not input_text.strip():
            raise GeminiError("La API de decisiones necesita una entrada con texto.")
        if not isinstance(questions, dict) or not questions:
            raise GeminiError("La API de decisiones necesita al menos una pregunta.")
        if len(questions) > _MAX_QUESTIONS:
            raise GeminiError(f"La API de decisiones admite hasta {_MAX_QUESTIONS} preguntas por petición.")
        for key, question in questions.items():
            if not _KEY_PATTERN.fullmatch(str(key)):
                raise GeminiError(f"Clave de pregunta inválida: '{key}'.")
            if not isinstance(question, dict) or question.get("type") not in QUESTION_TYPES:
                raise GeminiError(f"Pregunta '{key}' sin un tipo válido (noul, choice o score).")
            if not str(question.get("instructions") or "").strip():
                raise GeminiError(f"Pregunta '{key}' sin instrucciones.")

        payload = {
            "model": self.model_name,
            "input": input_text,
            "questions": questions,
        }
        body = self._post(payload)
        answers = self._read_answers(body)
        usage = self._read_usage(body)
        self.usage = DecisionUsage(
            total_input_tokens=self.usage.total_input_tokens + usage.total_input_tokens,
            total_output_tokens=self.usage.total_output_tokens + usage.total_output_tokens,
        )
        return answers, usage

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=DECISIONS_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
                "User-Agent": "DaVinciFlow/0.3.1",
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                detail = self._error_detail(error)
                if error.code in (401, 403):
                    raise GeminiCredentialsError(
                        "Clave API de Gemini rechazada o permisos insuficientes para la API de "
                        f"decisiones (HTTP {error.code})." + detail
                    ) from error
                if error.code == 400 and "safety" in detail.lower():
                    raise GeminiError("La API de decisiones bloqueó la petición por seguridad." + detail) from error
                if error.code == 429:
                    raise GeminiError(
                        "Límite de cuota o tasa de peticiones excedida en la API de decisiones (HTTP 429)." + detail
                    ) from error
                if error.code >= 500 and attempt < 2:
                    time.sleep(2.0 ** (attempt + 1) + random.uniform(0.0, 0.5))
                    continue
                raise GeminiError(
                    f"Error en la API de decisiones (HTTP {error.code})." + detail
                ) from error
            except TimeoutError as error:
                if attempt < 2:
                    time.sleep(2.0 ** (attempt + 1))
                    continue
                raise GeminiError(
                    f"La API de decisiones excedió el tiempo límite tras {attempt + 1} intento(s)."
                ) from error
            except urllib.error.URLError as error:
                raise GeminiError(f"No se pudo conectar con la API de decisiones de Google: {error.reason}") from error
            except GeminiError:
                raise
            except Exception as error:
                raise GeminiError("Error inesperado al consultar la API de decisiones.") from error
        raise GeminiError("No se pudo completar la petición a la API de decisiones.")

    def _error_detail(self, error: urllib.error.HTTPError) -> str:
        try:
            body = error.read().decode("utf-8")
        except Exception:
            body = ""
        finally:
            try:
                error.close()
            except Exception:
                pass
        message = ""
        try:
            payload = json.loads(body)
            message = str(payload.get("error", {}).get("message") or "")
        except (ValueError, AttributeError):
            message = ""
        message = message.replace(self._api_key, "[clave oculta]")
        message = re.sub(r"AIza[\w-]+", "[clave oculta]", message)
        return f" Detalle: {message[:400]}" if message else ""

    def _read_answers(self, body: dict[str, Any]) -> dict[str, DecisionAnswer]:
        raw_answers = body.get("answers")
        if not isinstance(raw_answers, dict) or not raw_answers:
            raise GeminiError("La API de decisiones no devolvió respuestas.")
        answers: dict[str, DecisionAnswer] = {}
        for key, raw in raw_answers.items():
            if not isinstance(raw, dict):
                continue
            probabilities = {
                str(name): float(value)
                for name, value in (raw.get("probabilities") or {}).items()
                if isinstance(value, (int, float))
            }
            legend = {str(name): str(value) for name, value in (raw.get("legend") or {}).items()}
            answers[str(key)] = DecisionAnswer(
                key=str(key),
                type=str(raw.get("type") or ""),
                noul=float(raw["noul"]) if isinstance(raw.get("noul"), (int, float)) else None,
                choice=str(raw["choice"]) if raw.get("choice") else None,
                score=float(raw["score"]) if isinstance(raw.get("score"), (int, float)) else None,
                probabilities=probabilities,
                confidence=float(raw.get("confidence") or 0.0),
                legend=legend,
            )
        if not answers:
            raise GeminiError("La API de decisiones no devolvió respuestas utilizables.")
        return answers

    def _read_usage(self, body: dict[str, Any]) -> DecisionUsage:
        raw = body.get("usage") or {}
        if not isinstance(raw, dict):
            raw = {}
        return DecisionUsage(
            total_input_tokens=int(raw.get("total_input_tokens") or 0),
            total_output_tokens=int(raw.get("total_output_tokens") or 0),
        )
