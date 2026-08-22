"""Pruebas del preflight de conexión con Resolve."""

import unittest
from unittest.mock import patch

from davinci_flow.errors import ResolveConnectionError
from davinci_flow.resolve.client import _validate_external_python_runtime, connect_to_resolve


class ResolveClientTests(unittest.TestCase):
    @patch("davinci_flow.resolve.client._is_resolve_running", return_value=False)
    def test_stops_before_loading_native_module_when_resolve_is_closed(self, _) -> None:
        with self.assertRaisesRegex(ResolveConnectionError, "no está en ejecución"):
            connect_to_resolve()

    @patch("davinci_flow.resolve.client.sys.platform", "win32")
    def test_rejects_incompatible_external_python_before_native_load(self) -> None:
        with patch("davinci_flow.resolve.client.sys.version_info", (3, 11, 0)):
            with self.assertRaisesRegex(ResolveConnectionError, "Python 3.13"):
                _validate_external_python_runtime()


if __name__ == "__main__":
    unittest.main()
