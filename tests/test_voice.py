"""Pruebas unitarias del motor de voz con Minimax."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from davinci_flow.errors import VoiceSynthesisError
from davinci_flow.voice.tts import (
    MinimaxSpeechClient,
    SpeechRequest,
    parse_subtitle_payload,
)


def _ok_response(payload):
    import io

    class _FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()
            return False

    def _factory(*args, **kwargs):
        return _FakeResponse(json.dumps(payload).encode("utf-8"))

    return _factory


class SubtitleParsingTests(unittest.TestCase):
    """Verifica la conversión del archivo de subtítulos de Minimax."""

    def test_parses_list_payload(self) -> None:
        payload = [
            {"text": "Hola", "time_begin": 0, "time_end": 1500},
            {"text": "Adiós", "time_begin": 1500, "time_end": 3000},
        ]
        cues = parse_subtitle_payload(payload)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text, "Hola")
        self.assertEqual(cues[1].end_ms, 3000)

    def test_parses_dict_payload(self) -> None:
        payload = {"subtitle": [{"text": "Hola", "time_begin": 0, "time_end": 900}]}
        cues = parse_subtitle_payload(payload)
        self.assertEqual(len(cues), 1)

    def test_discards_invalid_segments(self) -> None:
        payload = [
            {"text": "", "time_begin": 0, "time_end": 100},
            {"text": "Sin final", "time_begin": 200, "time_end": 100},
        ]
        self.assertEqual(parse_subtitle_payload(payload), ())

    def test_unknown_payload_is_empty(self) -> None:
        self.assertEqual(parse_subtitle_payload({"otro": 1}), ())


class SpeechClientTests(unittest.TestCase):
    """Verifica la síntesis de voz contra el endpoint oficial."""

    def setUp(self) -> None:
        self.client = MinimaxSpeechClient(api_key="clave-de-prueba")

    def test_synthesize_decodes_hex_and_reads_metadata(self) -> None:
        audio_hex = "0102030405"
        payload = {
            "data": {"audio": audio_hex, "status": 2},
            "extra_info": {
                "audio_length": 2400,
                "audio_sample_rate": 32000,
                "audio_format": "wav",
            },
            "trace_id": "abc123",
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            result = self.client.synthesize(SpeechRequest(text="Hola mundo"))

        self.assertEqual(result.audio, bytes.fromhex(audio_hex))
        self.assertEqual(result.duration_ms, 2400)
        self.assertEqual(result.audio_format, "wav")
        self.assertEqual(result.trace_id, "abc123")

    def test_request_uses_official_endpoint(self) -> None:
        captured = {}

        def _factory(request, timeout=None, **kwargs):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
            return _ok_response(
                {"data": {"audio": "00"}, "extra_info": {}, "base_resp": {"status_code": 0}}
            )()

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory):
            self.client.synthesize(SpeechRequest(text="Hola", voice_id="English_Graceful_Lady"))

        self.assertEqual(captured["url"], "https://api.minimax.io/v1/t2a_v2")
        self.assertEqual(captured["authorization"], "Bearer clave-de-prueba")
        self.assertEqual(captured["body"]["voice_setting"]["voice_id"], "English_Graceful_Lady")
        self.assertTrue(captured["body"]["subtitle_enable"])
        self.assertEqual(captured["body"]["audio_setting"]["format"], "wav")

    def test_empty_text_is_rejected(self) -> None:
        with self.assertRaises(VoiceSynthesisError):
            self.client.synthesize(SpeechRequest(text="   "))

    def test_too_long_text_is_rejected(self) -> None:
        with self.assertRaises(VoiceSynthesisError):
            self.client.synthesize(SpeechRequest(text="a" * 10001))

    def test_missing_audio_is_reported(self) -> None:
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response({"data": {}, "base_resp": {"status_code": 0}})):
            with self.assertRaises(VoiceSynthesisError):
                self.client.synthesize(SpeechRequest(text="Hola"))

    def test_base_resp_error_is_reported(self) -> None:
        payload = {"base_resp": {"status_code": 2013, "status_msg": "invalid input parameters"}}
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            with self.assertRaises(VoiceSynthesisError) as context:
                self.client.synthesize(SpeechRequest(text="Hola"))
        self.assertIn("2013", str(context.exception))

    def test_authentication_error_raises_credentials_error(self) -> None:
        from davinci_flow.errors import MinimaxCredentialsError

        payload = {"base_resp": {"status_code": 1004, "status_msg": "authentication failed"}}
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            with self.assertRaises(MinimaxCredentialsError):
                self.client.synthesize(SpeechRequest(text="Hola"))

    def test_synthesize_to_file_writes_audio(self) -> None:
        payload = {
            "data": {"audio": "0102"},
            "extra_info": {"audio_length": 100},
            "base_resp": {"status_code": 0},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "sub" / "voz.wav"
            with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
                result, path = self.client.synthesize_to_file(SpeechRequest(text="Hola"), target)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), bytes.fromhex("0102"))
            self.assertEqual(result.duration_ms, 100)

    def test_list_voices_parses_catalog(self) -> None:
        payload = {
            "system_voice": [
                {"voice_id": "English_Graceful_Lady", "voice_name": "Graceful Lady", "description": ["Suave"]},
                {"voice_id": "", "voice_name": "inválida"},
            ],
            "base_resp": {"status_code": 0},
        }
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            voices = self.client.list_voices()
        self.assertEqual(len(voices), 1)
        self.assertEqual(voices[0].voice_id, "English_Graceful_Lady")
        self.assertEqual(voices[0].description, ("Suave",))


if __name__ == "__main__":
    unittest.main()
