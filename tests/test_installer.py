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
            with patch("davinci_flow.installer.get_resolve_scripts_directory", return_value=fake_scripts_dir), \
                 patch('davinci_flow.installer.find_installed_desktop', return_value=None):
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

    def test_development_setup_preserves_installed_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / LAUNCHER_SCRIPT_NAME
            launcher.write_text('installed launcher', encoding='utf-8')
            with patch('davinci_flow.installer.get_resolve_scripts_directory', return_value=root), \
                 patch('davinci_flow.installer.find_installed_desktop', return_value=root/'DaVinciFlow.exe'):
                self.assertEqual(install_resolve_launcher(), launcher)
            self.assertEqual(launcher.read_text(encoding='utf-8'), 'installed launcher')

    def test_installed_app_uses_canonical_launcher(self):
        """Con la aplicación instalada, el menú de Resolve usa el lanzador canónico."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("davinci_flow.installer.get_resolve_scripts_directory", return_value=root), \
                 patch('davinci_flow.installer.find_installed_desktop', return_value=root / 'DaVinciFlow.exe'):
                installed_path = install_resolve_launcher()
                content = installed_path.read_text(encoding='utf-8')
            self.assertIn('_find_installed_exe', content)
            self.assertNotIn('open_davinci_flow_ui', content)

    def test_menu_always_launches_installed_binary_without_importing_development(self):
        namespace = {'__name__': 'launcher_test'}
        exec(compile(get_launcher_code(Path("D:/Dev/Con 'comillas'/src")), '<launcher>', 'exec'), namespace)
        executable = Path('C:/Apps/DaVinciFlow.exe')
        namespace['_find_installed_exe'] = lambda: executable
        with patch('subprocess.Popen') as spawn, patch('sys.path', []) as paths:
            namespace['main']()
            self.assertEqual(paths, [])
        self.assertEqual(spawn.call_args.args[0], [str(executable)])


if __name__ == "__main__":
    unittest.main()
