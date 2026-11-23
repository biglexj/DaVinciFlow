"""Pruebas unitarias para el módulo de auto-actualizaciones de DaVinci Flow."""

import json
import unittest
from unittest.mock import Mock, patch
import urllib.error

from davinci_flow.updater.checker import (
    UpdateRelease,
    check_github_release,
    is_newer_version,
    parse_update_release,
    sanitize_release_notes,
)


class UpdaterTests(unittest.TestCase):
    def test_is_newer_version_comparisons(self):
        self.assertTrue(is_newer_version("0.3.0", "0.3.1"))
        self.assertTrue(is_newer_version("0.3.0", "0.4.0"))
        self.assertTrue(is_newer_version("0.3.0", "1.0.0"))
        self.assertTrue(is_newer_version("v0.3.0", "v0.3.1"))
        self.assertTrue(is_newer_version("0.3.0", "0.3.0.1"))

        self.assertFalse(is_newer_version("0.3.0", "0.3.0"))
        self.assertFalse(is_newer_version("0.3.1", "0.3.0"))
        self.assertFalse(is_newer_version("1.0.0", "0.9.9"))
        self.assertFalse(is_newer_version("1.1.0", "1.0.9"))

    def test_sanitize_release_notes(self):
        raw = """
        # Novedades de la versión 0.3.1
        Esta actualización incluye **mejoras visuales** y corrección de *bugs*.
        - Nuevo panel de actualizaciones en `Ajustes`
        * Soporte para [descargas oficiales](https://github.com/biglexj)
        <div>Etiqueta HTML a ignorar</div>
        Archivo interno en C:\\Users\\biglexj\\DaVinciFlow\\temp
        """
        clean = sanitize_release_notes(raw)
        self.assertNotIn("#", clean)
        self.assertNotIn("**", clean)
        self.assertNotIn("<div>", clean)
        self.assertIn("Novedades de la versión 0.3.1:", clean)
        self.assertIn("• Nuevo panel de actualizaciones en Ajustes", clean)
        self.assertIn("• Soporte para descargas oficiales", clean)
        self.assertNotIn("C:\\Users\\biglexj", clean)

    def test_sanitize_release_notes_fallback_when_empty(self):
        self.assertIn("Actualización con mejoras", sanitize_release_notes(""))
        self.assertIn("Actualización con mejoras", sanitize_release_notes("   \n   "))

    def test_parse_update_release_prioritizes_binary_over_checksums(self):
        sample_json = {
            "tag_name": "v0.4.0",
            "html_url": "https://github.com/biglexj/DaVinciFlow/releases/tag/v0.4.0",
            "body": "## Cambios clave\n- Optimización en DaVinci Resolve",
            "published_at": "2026-09-08T10:00:00Z",
            "assets": [
                {
                    "name": "SHA256SUMS.txt",
                    "browser_download_url": "https://github.com/.../SHA256SUMS.txt",
                },
                {
                    "name": "DaVinciFlow-v0.4.0-windows.zip",
                    "browser_download_url": "https://github.com/.../DaVinciFlow-v0.4.0-windows.zip",
                },
            ],
        }

        release = parse_update_release(sample_json, current_version="0.3.0")
        self.assertIsNotNone(release)
        self.assertEqual(release.version, "0.4.0")
        self.assertTrue(release.is_newer)
        self.assertEqual(release.download_url, "https://github.com/.../DaVinciFlow-v0.4.0-windows.zip")
        self.assertIn("Cambios clave:", release.sanitized_notes)

    def test_parse_update_release_invalid_json(self):
        self.assertIsNone(parse_update_release("{invalid json}"))
        self.assertIsNone(parse_update_release({}))

    def test_check_github_release_success(self):
        payload = json.dumps({
            "tag_name": "v0.3.5",
            "html_url": "https://github.com/biglexj/DaVinciFlow/releases/tag/v0.3.5",
            "body": "Nueva versión disponible",
            "assets": [],
        }).encode("utf-8")

        mock_resp = Mock()
        mock_resp.status = 200
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            rel = check_github_release(current_version="0.3.0")
            self.assertIsNotNone(rel)
            self.assertEqual(rel.version, "0.3.5")
            self.assertTrue(rel.is_newer)

    def test_check_github_release_not_found_or_network_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 404, "Not Found", None, None)):
            rel = check_github_release()
            self.assertIsNone(rel)


if __name__ == "__main__":
    unittest.main()
