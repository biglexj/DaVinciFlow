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


if __name__ == "__main__":
    unittest.main()
