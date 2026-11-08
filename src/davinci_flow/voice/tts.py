"""Síntesis de voz con la API de Minimax.

Aporta lo que el editor no tenía: locución generada, con los subtítulos alineados a
la propia voz. La API oficial `t2a_v2` devuelve el audio como cadena hexadecimal y,
si se pide, un archivo de subtítulos con las marcas de tiempo en milisegundos.

Referencias:
- `POST https://api.minimax.io/v1/t2a_v2` (texto a audio síncrono).
- `POST https://api.minimax.io/v1/get_voice` (catálogo de voces de la cuenta).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from davinci_flow.ai.credentials import get_minimax_api_key
from davinci_flow.ai.http import DEFAULT_TIMEOUT_SECONDS, post_json, sanitize_detail
from davinci_flow.errors import MinimaxCredentialsError, VoiceSynthesisError

API_BASE_URL = "https://api.minimax.io/v1"
SPEECH_PATH = "/t2a_v2"
VOICE_PATH = "/get_voice"

DEFAULT_SPEECH_MODEL = "speech-2.8-hd"
SPEECH_MODELS = (
    "speech-2.8-hd",
    "speech-2.8-turbo",
    "speech-2.6-hd",
    "speech-2.6-turbo",
    "speech-02-hd",
    "speech-02-turbo",
    "speech-01-hd",
    "speech-01-turbo",
)
DEFAULT_VOICE_ID = "English_Graceful_Lady"
MAX_TEXT_CHARS = 10000
AUTH_FAILED_STATUS = 1004


@dataclass(frozen=True)
class VoiceInfo:
    """Una voz disponible en la cuenta de Minimax."""

    voice_id: str
    voice_name: str = ""
    description: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeechRequest:
    """Parámetros de una síntesis de voz."""

    text: str
    voice_id: str = DEFAULT_VOICE_ID
    model: str = DEFAULT_SPEECH_MODEL
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0
    emotion: str = ""
    language_boost: str = "auto"
    audio_format: str = "wav"
    sample_rate: int = 32000
    channel: int = 1
    with_subtitles: bool = True
    subtitle_granularity: str = "sentence"


@dataclass(frozen=True)
class SpeechCue:
    """Una frase de la locución con sus marcas de tiempo."""

    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class SpeechResult:
    """Audio sintetizado y subtítulos alineados."""

    audio: bytes
    audio_format: str
    duration_ms: int
    sample_rate: int
    cues: tuple[SpeechCue, ...] = ()
    trace_id: str = ""
    voice_id: str = ""
    model: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


class MinimaxSpeechClient:
    """Cliente de locución de Minimax."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._api_key = get_minimax_api_key(api_key)
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")

    def list_voices(self, voice_type: str = "system") -> tuple[VoiceInfo, ...]:
        """Devuelve las voces disponibles en la cuenta."""
        response = post_json(
            url=f"{self.base_url}{VOICE_PATH}",
            payload={"voice_type": voice_type},
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout_seconds=self.timeout_seconds,
            error_type=VoiceSynthesisError,
            auth_error_type=MinimaxCredentialsError,
            secrets=(self._api_key,),
        )
        self._raise_for_status(response)

        voices: list[VoiceInfo] = []
        for entry in response.get("system_voice") or []:
            voice_id = str(entry.get("voice_id") or "").strip()
            if not voice_id:
                continue
            description = entry.get("description")
            if isinstance(description, str):
                description = (description,)
            voices.append(
                VoiceInfo(
                    voice_id=voice_id,
                    voice_name=str(entry.get("voice_name") or "").strip(),
                    description=tuple(str(item) for item in (description or ())),
                )
            )
        return tuple(voices)

    def synthesize(self, request: SpeechRequest) -> SpeechResult:
        """Sintetiza la locución y devuelve el audio con sus subtítulos alineados."""
        text = request.text.strip()
        if not text:
            raise VoiceSynthesisError("El texto de la locución está vacío.")
        if len(text) > MAX_TEXT_CHARS:
            raise VoiceSynthesisError(
                f"El texto supera los {MAX_TEXT_CHARS} caracteres admitidos por la API."
            )

        voice_setting: dict[str, Any] = {
            "voice_id": request.voice_id,
            "speed": max(0.5, min(float(request.speed), 2.0)),
            "vol": max(0.01, min(float(request.volume), 10.0)),
            "pitch": max(-12, min(int(request.pitch), 12)),
        }
        if request.emotion:
            voice_setting["emotion"] = request.emotion

        payload: dict[str, Any] = {
            "model": request.model,
            "text": text,
            "stream": False,
            "output_format": "hex",
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": request.sample_rate,
                "format": request.audio_format,
                "channel": request.channel,
            },
            "language_boost": request.language_boost or "auto",
        }
        if request.with_subtitles:
            payload["subtitle_enable"] = True
            payload["subtitle_type"] = request.subtitle_granularity

        response = post_json(
            url=f"{self.base_url}{SPEECH_PATH}",
            payload=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout_seconds=self.timeout_seconds,
            error_type=VoiceSynthesisError,
            auth_error_type=MinimaxCredentialsError,
            secrets=(self._api_key,),
        )
        self._raise_for_status(response)

        data = response.get("data") or {}
        raw_audio = data.get("audio")
        if not isinstance(raw_audio, str) or not raw_audio.strip():
            raise VoiceSynthesisError("Minimax devolvió una respuesta sin audio.")
        try:
            audio = bytes.fromhex(raw_audio.strip())
        except ValueError as err:
            raise VoiceSynthesisError(f"El audio de Minimax no es hexadecimal válido: {err}") from err

        extra_info = response.get("extra_info") or {}
        cues: tuple[SpeechCue, ...] = ()
        subtitle_url = data.get("subtitle_file")
        if isinstance(subtitle_url, str) and subtitle_url.strip():
            cues = self._load_subtitles(subtitle_url.strip())

        return SpeechResult(
            audio=audio,
            audio_format=str(extra_info.get("audio_format") or request.audio_format),
            duration_ms=int(extra_info.get("audio_length") or 0),
            sample_rate=int(extra_info.get("audio_sample_rate") or request.sample_rate),
            cues=cues,
            trace_id=str(response.get("trace_id") or ""),
            voice_id=request.voice_id,
            model=request.model,
            extras={
                "usage_characters": extra_info.get("usage_characters"),
                "word_count": extra_info.get("word_count"),
                "audio_size": extra_info.get("audio_size"),
            },
        )

    def synthesize_to_file(self, request: SpeechRequest, path: Path) -> tuple[SpeechResult, Path]:
        """Sintetiza la locución y guarda el audio en disco."""
        result = self.synthesize(request)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.audio)
        return result, path

    def _raise_for_status(self, response: dict[str, Any]) -> None:
        """Valida ``base_resp``, que reporta errores lógicos con HTTP 200."""
        base_resp = response.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code in (None, 0):
            return
        status_msg = str(base_resp.get("status_msg") or "error desconocido")
        if status_code == AUTH_FAILED_STATUS:
            raise MinimaxCredentialsError(f"Minimax rechazó la autenticación: {status_msg}")
        raise VoiceSynthesisError(f"Minimax rechazó la solicitud (código {status_code}): {status_msg}")

    def _load_subtitles(self, url: str) -> tuple[SpeechCue, ...]:
        """Descarga el archivo de subtítulos y lo convierte en marcas de tiempo."""
        payload = self._download_json(url)
        if payload is None:
            return ()
        return parse_subtitle_payload(payload)


def _download_json(url: str, api_key: str | None = None) -> Any:
    """Descarga un JSON público; si el servidor lo exige, reintenta con la credencial."""
    attempts = [(url, None)]
    if api_key:
        separator = "&" if "?" in url else "?"
        attempts.append((f"{url}{separator}Authorization={api_key}", api_key))

    last_error: Exception | None = None
    for target, key in attempts:
        headers = {"User-Agent": "DaVinciFlow/0.2.0"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        request = urllib.request.Request(url=target, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_error = err
    raise VoiceSynthesisError(
        f"No se pudo descargar el archivo de subtítulos de Minimax: {sanitize_detail(str(last_error))}"
    )


def parse_subtitle_payload(payload: Any) -> tuple[SpeechCue, ...]:
    """Convierte la estructura de subtítulos de Minimax en marcas de tiempo.

    Acepta una lista directa de segmentos o un diccionario con las claves habituales
    (``subtitle``, ``subtitles``, ``segments``). Cada segmento trae ``text``,
    ``time_begin`` y ``time_end`` en milisegundos.
    """
    segments: Iterable[Any]
    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        for key in ("subtitle", "subtitles", "segments", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                segments = value
                break
        else:
            segments = ()
    else:
        segments = ()

    cues: list[SpeechCue] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start = _to_int(segment.get("time_begin"))
        end = _to_int(segment.get("time_end"))
        if end <= start:
            continue
        cues.append(SpeechCue(text=text, start_ms=start, end_ms=end))
    return tuple(cues)


def _to_int(value: Any) -> int:
    """Convierte a milisegundos enteros un valor numérico o textual."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def save_speech_audio(result: SpeechResult, path: Path) -> Path:
    """Guarda el audio sintetizado en disco y devuelve la ruta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result.audio)
    return path
