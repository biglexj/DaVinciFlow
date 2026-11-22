"""Regresiones del bundle congelado: el ejecutable instalado debe abrir.

El ejecutable de Windows se compila con PyInstaller, que solo detecta imports
estaticos. Las vistas de la interfaz se importan en tiempo de ejecucion, asi
que el bundle las declara de forma explicita. Estas pruebas vigilan ese
contrato: si una vista nueva entra en `VIEW_TYPES` sin llegar al bundle, la
aplicacion instalada muere al arrancar.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_FLET = REPO_ROOT / "src-flet"
if str(SRC_FLET) not in sys.path:
    sys.path.insert(0, str(SRC_FLET))

MANIFEST_PATH = REPO_ROOT / "scripts" / "packaging" / "flet_view_manifest.py"
SPEC_PATH = REPO_ROOT / "packaging" / "windows" / "launcher" / "DaVinciFlow.spec"


def _load_manifest():
    spec = importlib.util.spec_from_file_location("flet_view_manifest", MANIFEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FrozenBundleTests(unittest.TestCase):
    """Verifica que el bundle declarado contiene todo lo que la app carga en runtime."""

    def setUp(self) -> None:
        self.manifest = _load_manifest()

    def test_manifest_matches_registered_views(self) -> None:
        from app.views import VIEW_TYPES

        registered = [module for module, _, _ in VIEW_TYPES.values()]
        self.assertEqual(self.manifest.view_modules(REPO_ROOT), registered)
        self.assertTrue(registered)

    def test_view_modules_exist_and_import(self) -> None:
        for module in self.manifest.view_modules(REPO_ROOT):
            with self.subTest(module=module):
                path = REPO_ROOT / "src-flet" / Path(*module.split(".")).with_suffix(".py")
                self.assertTrue(path.is_file(), f"Falta el modulo de la vista: {module}")
                self.assertTrue(importlib.import_module(module))

    def test_interface_packages_are_regular_packages(self) -> None:
        """Un paquete sin `__init__.py` no lo recorre PyInstaller al recoger modulos."""
        missing = self.manifest.namespace_packages(REPO_ROOT)
        self.assertEqual(missing, [], f"Paquetes sin __init__.py: {missing}")

    def test_spec_declares_lazy_views_and_submodules(self) -> None:
        spec_text = SPEC_PATH.read_text(encoding="utf-8")
        self.assertIn("flet_view_manifest", spec_text)
        self.assertIn("collect_submodules", spec_text)
        self.assertIn('"davinci_flow"', spec_text)

    def test_canonical_resolve_launcher_is_valid_and_targets_installed_app(self) -> None:
        launcher = REPO_ROOT / "packaging" / "windows" / "resolve" / "DaVinci Flow.py"
        self.assertTrue(launcher.is_file())
        source = launcher.read_text(encoding="utf-8")
        compile(source, str(launcher), "exec")
        self.assertIn("DaVinciFlow.exe", source)

    def test_installer_uses_canonical_launcher_when_app_is_installed(self) -> None:
        from davinci_flow.installer import find_canonical_launcher, get_canonical_launcher_code

        canonical = find_canonical_launcher()
        self.assertIsNotNone(canonical)
        code = get_canonical_launcher_code()
        self.assertTrue(code)
        self.assertIn("_find_installed_exe", code)
        self.assertNotIn("open_davinci_flow_ui", code)


if __name__ == "__main__":
    unittest.main()
