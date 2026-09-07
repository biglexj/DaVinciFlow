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


if __name__ == "__main__":
    unittest.main()

