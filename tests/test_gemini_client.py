"""Pruebas unitarias para el cliente HTTP de Gemini."""

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from davinci_flow.ai.client import GeminiClient
from davinci_flow.errors import GeminiCredentialsError, GeminiError


class GeminiClientTests(unittest.TestCase):
    """Verifica el funcionamiento del cliente HTTP ligero para Google Gemini."""

    def setUp(self) -> None:
        self.client = GeminiClient(api_key="AIzaSyTestKey123456789")

    @patch("urllib.request.urlopen")
    def test_generate_json_success(self, mock_urlopen: MagicMock) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"status": "ok", "corrected": "Prueba de texto"})}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = self.client.generate_json("Corrige esto")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("status"), "ok")
        self.assertEqual(result.get("corrected"), "Prueba de texto")

    @patch("urllib.request.urlopen")
    def test_generate_text_success(self, mock_urlopen: MagicMock) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Respuesta en texto plano"}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = self.client.generate_text("Hola")
        self.assertEqual(result, "Respuesta en texto plano")

    @patch("urllib.request.urlopen")
    def test_test_connection_returns_true(self, mock_urlopen: MagicMock) -> None:
        mock_response_data = {
            "candidates": [
                {"content": {"parts": [{"text": "OK"}]}}
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        self.assertTrue(self.client.test_connection())

    @patch("urllib.request.urlopen")
    def test_http_401_raises_credentials_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.test",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error": "API key invalid"}'),
        )
        with self.assertRaises(GeminiCredentialsError):
            self.client.generate_text("Hola")

    @patch("urllib.request.urlopen")
    def test_http_429_raises_gemini_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.test",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"error": "Quota exceeded"}'),
        )
        with self.assertRaises(GeminiError):
            self.client.generate_text("Hola")

    @patch("urllib.request.urlopen")
    def test_invalid_json_payload_raises_gemini_error(self, mock_urlopen: MagicMock) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Texto que no es JSON"}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with self.assertRaises(GeminiError):
            self.client.generate_json("Dame un JSON")


class ListAvailableModelsTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_list_available_models_filters_and_sorts(self, mock_urlopen: MagicMock) -> None:
        from davinci_flow.ai.client import list_available_gemini_models

        mock_payload = {
            "models": [
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
                {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.7-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = list_available_gemini_models(api_key="AIzaSyDummy123456")
        self.assertIn("gemini-3.5-flash-lite", models)
        self.assertIn("gemini-3.5-flash", models)
        self.assertIn("gemini-3.7-flash", models)
        self.assertNotIn("gemini-2.5-pro", models)
        self.assertNotIn("text-embedding-004", models)

    def test_list_available_models_fallback_on_empty_or_error(self) -> None:
        from davinci_flow.ai.client import FALLBACK_MODELS, list_available_gemini_models

        with patch("davinci_flow.ai.client.get_gemini_api_key", side_effect=Exception("No key")):
            models = list_available_gemini_models(api_key=None)
            self.assertEqual(models, FALLBACK_MODELS)


class GeminiRecoveryTests(unittest.TestCase):
    def error(self, code=503, message="Servicio ocupado", headers=None):
        return urllib.error.HTTPError(
            "https://api.test", code, "error", headers or {},
            io.BytesIO(json.dumps({"error": {"status": "UNAVAILABLE", "message": message}}).encode()),
        )

    @patch("davinci_flow.ai.client.time.sleep")
    @patch("urllib.request.urlopen")
    def test_transient_error_recovers_with_identical_request(self, request, sleep):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}'
        request.side_effect = [self.error(headers={"Retry-After": "3"}), response]
        client = GeminiClient(api_key="secret-key", model_name="chosen-model", strict_model=True)
        self.assertEqual(client.generate_text("Hola"), "OK")
        self.assertIs(request.call_args_list[0].args[0], request.call_args_list[1].args[0])
        self.assertEqual(client.model_name, "chosen-model")
        sleep.assert_called_once_with(3.0)

    @patch("davinci_flow.ai.client.time.sleep")
    @patch("urllib.request.urlopen")
    def test_persistent_error_is_bounded_and_preserves_safe_detail(self, request, sleep):
        request.side_effect = [self.error(message="Sobrecarga secret-key") for _ in range(3)]
        client = GeminiClient(api_key="secret-key", model_name="chosen-model")
        with self.assertRaises(GeminiError) as result:
            client.generate_json("Prueba")
        message = str(result.exception)
        self.assertIn("503", message)
        self.assertIn("3 intento", message)
        self.assertIn("UNAVAILABLE", message)
        self.assertIn("Sobrecarga", message)
        self.assertNotIn("secret-key", message)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(client.model_name, "chosen-model")

    @patch("davinci_flow.ai.client.time.sleep")
    @patch("urllib.request.urlopen")
    def test_timeout_retries_once_and_recovers(self, request, sleep):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}'
        request.side_effect = [TimeoutError("demora"), response]
        client = GeminiClient(api_key="secret-key", model_name="chosen-model", strict_model=True)
        self.assertEqual(client.generate_text("Hola"), "OK")
        self.assertEqual(request.call_count, 2)
        self.assertEqual(client.model_name, "chosen-model")
        sleep.assert_called_once()

    @patch("davinci_flow.ai.client.time.sleep")
    @patch("urllib.request.urlopen", side_effect=TimeoutError("demora"))
    def test_persistent_timeout_is_bounded_and_identifies_model(self, request, sleep):
        client = GeminiClient(api_key="secret-key", model_name="chosen-model", strict_model=True)
        with self.assertRaises(GeminiError) as result:
            client.generate_text("Hola")
        self.assertIn("2 intento", str(result.exception))
        self.assertIn("chosen-model", str(result.exception))
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once()

    @patch("davinci_flow.ai.client.time.sleep")
    @patch("urllib.request.urlopen")
    def test_permanent_errors_and_quota_are_not_retried(self, request, sleep):
        for code in (400, 401, 403, 404, 429):
            request.reset_mock()
            request.side_effect = self.error(code=code)
            client = GeminiClient(api_key="secret-key", strict_model=True)
            with self.assertRaises((GeminiError, GeminiCredentialsError)):
                client.generate_text("Prueba")
            self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    def test_retry_after_is_bounded_and_supports_http_date(self):
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime
        from davinci_flow.ai.client import _retry_delay, _error_detail
        self.assertEqual(_retry_delay({"Retry-After": "999"}, 0), 30)
        self.assertEqual(_retry_delay({"Retry-After": "-2"}, 0), 0)
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20))
        self.assertTrue(18 <= _retry_delay({"Retry-After": future}, 0) <= 20)
        self.assertTrue(2 <= _retry_delay({"Retry-After": "invalid"}, 0) <= 3)
        self.assertEqual(_error_detail("<html>proxy error</html>", "key"), "")


if __name__ == "__main__":
    unittest.main()
