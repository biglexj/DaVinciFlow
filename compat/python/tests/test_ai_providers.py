"""Pruebas unitarias de la capa de proveedores de IA (Gemini y Minimax)."""

import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from davinci_flow.ai.credentials import (
    get_minimax_api_key,
    has_minimax_api_key,
    save_minimax_api_key,
)
from davinci_flow.ai.http import extract_json_payload
from davinci_flow.ai.providers.base import GEMINI_PROVIDER, MINIMAX_PROVIDER
from davinci_flow.ai.providers.factory import build_text_provider, default_model_for
from davinci_flow.ai.providers.gemini_provider import GeminiProvider
from davinci_flow.ai.providers.minimax_provider import MinimaxProvider
from davinci_flow.editorial.preferences import Preferences
from davinci_flow.errors import MinimaxCredentialsError, MinimaxError


class _FakeResponse(io.BytesIO):
    """Respuesta HTTP mínima para las pruebas."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def _json_response(payload, status=200, headers=None):
    """Construye un error HTTP simulado con cuerpo JSON."""

    def _factory(*args, **kwargs):
        body = json.dumps(payload).encode("utf-8")
        error = urllib.error.HTTPError("https://api.minimax.io", status, "error", headers or {}, io.BytesIO(body))
        return error

    return _factory


def _ok_response(payload):
    """Construye una respuesta HTTP exitosa."""

    def _factory(*args, **kwargs):
        return _FakeResponse(json.dumps(payload).encode("utf-8"))

    return _factory


class MinimaxProviderTests(unittest.TestCase):
    """Verifica el contrato del adaptador de Minimax contra el endpoint oficial."""

    def setUp(self) -> None:
        self.provider = MinimaxProvider(api_key="clave-de-prueba", model_name="MiniMax-M3")

    def test_generate_text_returns_content(self) -> None:
        payload = {
            "choices": [{"message": {"content": "  Hola  "}}],
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            result = self.provider.generate_text("Hola", system_instruction="Sé breve")
        self.assertEqual(result, "Hola")

    def test_request_uses_official_endpoint_and_headers(self) -> None:
        captured = {}

        def _factory(request, timeout=None, **kwargs):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
            return _FakeResponse(
                json.dumps(
                    {"choices": [{"message": {"content": "ok"}}], "base_resp": {"status_code": 0}}
                ).encode("utf-8")
            )

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory):
            self.provider.generate_text("Hola", system_instruction="Sistema")

        self.assertEqual(captured["url"], "https://api.minimax.io/v1/text/chatcompletion_v2")
        self.assertEqual(captured["authorization"], "Bearer clave-de-prueba")
        self.assertEqual(captured["body"]["model"], "MiniMax-M3")
        self.assertFalse(captured["body"]["stream"])
        self.assertEqual(captured["body"]["messages"][0]["role"], "system")
        self.assertEqual(captured["body"]["messages"][1]["role"], "user")

    def test_generate_json_parses_fenced_json(self) -> None:
        payload = {
            "choices": [{"message": {"content": "```json\n{\"a\": 1}\n```"}}],
            "base_resp": {"status_code": 0},
        }
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            result = self.provider.generate_json("Devuelve JSON")
        self.assertEqual(result, {"a": 1})

    def test_generate_json_raises_on_invalid_payload(self) -> None:
        payload = {
            "choices": [{"message": {"content": "esto no es json"}}],
            "base_resp": {"status_code": 0},
        }
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            with self.assertRaises(MinimaxError):
                self.provider.generate_json("Devuelve JSON")

    def test_base_resp_error_is_reported(self) -> None:
        payload = {"base_resp": {"status_code": 2013, "status_msg": "invalid input parameters"}}
        with patch("davinci_flow.ai.http.urllib.request.urlopen", _ok_response(payload)):
            with self.assertRaises(MinimaxError) as context:
                self.provider.generate_text("Hola")
        self.assertIn("2013", str(context.exception))

    def test_retries_on_server_error(self) -> None:
        calls = {"count": 0}

        def _factory(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                raise _json_response({"error": "temporal"}, status=503)()
            return _FakeResponse(
                json.dumps(
                    {"choices": [{"message": {"content": "ok"}}], "base_resp": {"status_code": 0}}
                ).encode("utf-8")
            )

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory), \
             patch("davinci_flow.ai.http.time.sleep"):
            result = self.provider.generate_text("Hola")

        self.assertEqual(result, "ok")
        self.assertEqual(calls["count"], 3)

    def test_does_not_retry_on_client_error(self) -> None:
        calls = {"count": 0}

        def _factory(*args, **kwargs):
            calls["count"] += 1
            raise _json_response({"error": "malformed"}, status=400)()

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory), \
             patch("davinci_flow.ai.http.time.sleep"):
            with self.assertRaises(MinimaxError):
                self.provider.generate_text("Hola")
        self.assertEqual(calls["count"], 1)

    def test_unauthorized_raises_credentials_error(self) -> None:
        def _factory(*args, **kwargs):
            raise _json_response({"error": "invalid api key"}, status=401)()

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory):
            with self.assertRaises(MinimaxCredentialsError):
                self.provider.generate_text("Hola")

    def test_error_message_hides_credentials(self) -> None:
        def _factory(*args, **kwargs):
            raise _json_response({"error": "clave-de-prueba invalida"}, status=400)()

        with patch("davinci_flow.ai.http.urllib.request.urlopen", _factory):
            with self.assertRaises(MinimaxError) as context:
                self.provider.generate_text("Hola")
        self.assertNotIn("clave-de-prueba", str(context.exception))


class ProviderFactoryTests(unittest.TestCase):
    """Verifica la fábrica de proveedores y el catálogo de modelos."""

    def test_builds_each_provider(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g"}, clear=False):
            gemini = build_text_provider(GEMINI_PROVIDER, "gemini-3.5-flash")
        minimax = build_text_provider(MINIMAX_PROVIDER, "MiniMax-M3", api_key="clave")
        self.assertIsInstance(gemini, GeminiProvider)
        self.assertIsInstance(minimax, MinimaxProvider)
        self.assertEqual(minimax.model_name, "MiniMax-M3")

    def test_empty_model_uses_provider_default(self) -> None:
        provider = build_text_provider(MINIMAX_PROVIDER, "", api_key="clave")
        self.assertEqual(provider.model_name, default_model_for(MINIMAX_PROVIDER))

    def test_unknown_provider_raises(self) -> None:
        with self.assertRaises(KeyError):
            build_text_provider("otro", "modelo", api_key="clave")


class MinimaxCredentialsTests(unittest.TestCase):
    """Verifica el almacenamiento de la clave de Minimax junto a la de Gemini."""

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_config = Path(tmp_dir) / "config.json"
            with patch("davinci_flow.ai.credentials.CONFIG_FILE", temp_config), \
                 patch("davinci_flow.ai.credentials.CONFIG_DIR", Path(tmp_dir)):
                save_minimax_api_key("clave-minimax")
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(get_minimax_api_key(), "clave-minimax")
                    self.assertTrue(has_minimax_api_key())

    def test_missing_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("davinci_flow.ai.credentials.load_user_config", return_value={}):
                with self.assertRaises(MinimaxCredentialsError):
                    get_minimax_api_key()
                self.assertFalse(has_minimax_api_key())


class PreferencesProviderTests(unittest.TestCase):
    """Verifica la compatibilidad de las preferencias con el campo de proveedor."""

    def test_legacy_preferences_default_to_gemini(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "prefs.json"
            path.write_text(json.dumps({"model": "gemini-3.5-flash"}), encoding="utf-8")
            preferences = Preferences.load(path)
        self.assertEqual(preferences.provider, GEMINI_PROVIDER)

    def test_minimax_resets_foreign_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "prefs.json"
            path.write_text(
                json.dumps({"provider": MINIMAX_PROVIDER, "model": "gemini-3.5-flash"}),
                encoding="utf-8",
            )
            preferences = Preferences.load(path)
        self.assertEqual(preferences.provider, MINIMAX_PROVIDER)
        self.assertEqual(preferences.model, default_model_for(MINIMAX_PROVIDER))

    def test_unknown_provider_is_rejected(self) -> None:
        preferences = Preferences(provider="otro")
        with self.assertRaises(Exception):
            preferences.validate()


class JsonExtractionTests(unittest.TestCase):
    """Verifica el saneado de respuestas JSON con texto alrededor."""

    def test_extracts_embedded_object(self) -> None:
        self.assertEqual(extract_json_payload('Aquí tienes: {"a": [1, 2]} listo'), {"a": [1, 2]})

    def test_extracts_embedded_array(self) -> None:
        self.assertEqual(extract_json_payload("texto [1, 2, 3]"), [1, 2, 3])

    def test_raises_without_json(self) -> None:
        with self.assertRaises(ValueError):
            extract_json_payload("sin json alguno")


if __name__ == "__main__":
    unittest.main()
