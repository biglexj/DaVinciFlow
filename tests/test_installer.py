"""Pruebas unitarias para el instalador de DaVinci Flow en Resolve."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from davinci_flow.installer import (
    LAUNCHER_SCRIPT_NAME,
    get_launcher_code,
    get_resolve_scripts_directory,
    install_resolve_launcher,
    uninstall_resolve_launcher,
)


class InstallerTests(unittest.TestCase):
    """Verifica la generación del código del lanzador y la instalación/desinstalación de scripts."""

    def test_get_launcher_code_contains_source_path(self) -> None:
        custom_path = Path("/custom/path/to/davinci_flow")
        code = get_launcher_code(custom_path)
        self.assertIn("/custom/path/to/davinci_flow", code)
        self.assertIn("open_davinci_flow_ui", code)

    def test_install_and_uninstall_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_scripts_dir = Path(tmpdir) / "Scripts" / "Utility"
            with patch("davinci_flow.installer.get_resolve_scripts_directory", return_value=fake_scripts_dir):
                installed_path = install_resolve_launcher()
                self.assertTrue(installed_path.is_file())
                self.assertEqual(installed_path.name, LAUNCHER_SCRIPT_NAME)

                content = installed_path.read_text(encoding="utf-8")
                self.assertIn("open_davinci_flow_ui", content)

                # Desinstalar
                removed = uninstall_resolve_launcher()
                self.assertTrue(removed)
                self.assertFalse(installed_path.exists())

                # Segunda desinstalación retorna False
                self.assertFalse(uninstall_resolve_launcher())


if __name__ == "__main__":
    unittest.main()
