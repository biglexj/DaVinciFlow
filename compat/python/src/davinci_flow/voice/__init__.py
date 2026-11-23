"""Locución sintética para DaVinci Flow."""

from davinci_flow.voice.tts import (
    DEFAULT_SPEECH_MODEL,
    DEFAULT_VOICE_ID,
    SPEECH_MODELS,
    MinimaxSpeechClient,
    SpeechCue,
    SpeechRequest,
    SpeechResult,
    VoiceInfo,
    parse_subtitle_payload,
    save_speech_audio,
)

__all__ = [
    "DEFAULT_SPEECH_MODEL",
    "DEFAULT_VOICE_ID",
    "SPEECH_MODELS",
    "MinimaxSpeechClient",
    "SpeechCue",
    "SpeechRequest",
    "SpeechResult",
    "VoiceInfo",
    "parse_subtitle_payload",
    "save_speech_audio",
]
