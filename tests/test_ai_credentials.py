"""Pruebas unitarias para la gestión segura de credenciales de Gemini."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from davinci_flow.ai.credentials import (
    get_gemini_api_key,
    has_gemini_api_key,
    load_user_config,
    mask_api_key,
    save_gemini_api_key,
)
from davinci_flow.errors import GeminiCredentialsError


class AiCredentialsTests(unittest.TestCase):
    """Verifica el almacenamiento seguro, enmascaramiento y resolución de claves API."""

    def test_mask_api_key(self) -> None:
        self.assertEqual(mask_api_key(""), "")
        self.assertEqual(mask_api_key("1234"), "********")
        self.assertEqual(mask_api_key("AIzaSy1234567890abcdef"), "AIza...cdef")

    def test_get_explicit_key(self) -> None:
        key = get_gemini_api_key("mi-clave-explicita")
        self.assertEqual(key, "mi-clave-explicita")

    def test_get_key_from_env(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "clave-desde-entorno"}):
            key = get_gemini_api_key()
            self.assertEqual(key, "clave-desde-entorno")
            self.assertTrue(has_gemini_api_key())

    def test_missing_key_raises_credentials_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("davinci_flow.ai.credentials.load_user_config", return_value={}):
                with self.assertRaises(GeminiCredentialsError):
                    get_gemini_api_key()
                self.assertFalse(has_gemini_api_key())

    def test_save_and_load_gemini_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_config = Path(tmp_dir) / "config.json"
            with patch("davinci_flow.ai.credentials.CONFIG_FILE", temp_config), \
                 patch("davinci_flow.ai.credentials.CONFIG_DIR", Path(tmp_dir)):
                save_gemini_api_key("clave-secreta-guardada")
                self.assertTrue(temp_config.is_file())

                loaded = load_user_config()
                self.assertEqual(loaded.get("gemini_api_key"), "clave-secreta-guardada")

                with patch.dict(os.environ, {}, clear=True):
                    resolved = get_gemini_api_key()
                    self.assertEqual(resolved, "clave-secreta-guardada")


if __name__ == "__main__":
    unittest.main()
