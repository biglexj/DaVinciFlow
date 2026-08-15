"""Pruebas del preflight de conexión con Resolve."""

import unittest
from unittest.mock import patch

from davinci_flow.errors import ResolveConnectionError
from davinci_flow.resolve.client import connect_to_resolve


class ResolveClientTests(unittest.TestCase):
    @patch("davinci_flow.resolve.client._is_resolve_running", return_value=False)
    def test_stops_before_loading_native_module_when_resolve_is_closed(self, _) -> None:
        with self.assertRaisesRegex(ResolveConnectionError, "no está en ejecución"):
            connect_to_resolve()


if __name__ == "__main__":
    unittest.main()
