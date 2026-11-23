"""Biblioteca real: DRB, muestras originales y selecciones reutilizables."""

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

from davinci_flow.editorial.controller import EditorialController
from davinci_flow.editorial.model import EditorialError, Template
from davinci_flow.editorial.sources import scan_installed
from davinci_flow.editorial.title_preview import read_title_preview, title_preview_kind
from davinci_flow.editorial.native_template import import_native_template
from davinci_flow.editorial.writer import EditorialWriter
from davinci_flow.user_data import user_data_dir
from tests.test_editorial_writer import setup


class TitleCatalogTests(unittest.TestCase):
    def test_drb_preview_is_original_companion_and_presets_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'Smooth Lift.drb'
            source.write_bytes(b'native-bin')
            source.with_suffix('.mp4').write_bytes(b'original-preview')
            templates = scan_installed((root,))
            self.assertEqual(len(templates), 1)
            template = templates[0]
            self.assertEqual(template.source, 'installed_bin')
            self.assertEqual(template.fingerprint, hashlib.sha256(b'native-bin').hexdigest())
            self.assertEqual(read_title_preview(template).video, source.with_suffix('.mp4'))
            self.assertEqual(title_preview_kind(template), 'video')
            path = root / 'prefs.json'
            controller = EditorialController(path)
            controller.catalog[template.id] = template
            controller.save_title_preset('Narrativa horizontal', {template.id})
            restarted = EditorialController(path)
            restarted.use_title_preset('Narrativa horizontal')
            self.assertEqual(restarted.templates, (template,))
            self.assertEqual(source.read_bytes(), b'native-bin')

    def test_archive_preview_uses_exact_member_and_ignores_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'Pack.drfx'
            with ZipFile(archive, 'w') as z:
                z.writestr('Edit/Titles/Real.setting', '{ Tools = ordered() {} }')
                z.writestr('Edit/Titles/Real.png', b'original-image')
                z.writestr('Other/Real.mp4', b'unrelated-video')
                z.writestr('__MACOSX/Edit/Titles/._Real.setting', b'\x00\xff')
            templates = scan_installed((root,))
            self.assertEqual(len(templates), 1)
            preview = read_title_preview(templates[0], root / 'cache')
            self.assertEqual(preview.image.read_bytes(), b'original-image')
            self.assertEqual(title_preview_kind(templates[0]), 'image')
            self.assertIsNone(preview.video)
            self.assertEqual(len(list((root / 'cache').iterdir())), 1)

    def test_no_preview_never_fabricates_one(self):
        template = Template('pool_title', 'Propio', 'media_pool', 'title')
        self.assertIsNone(read_title_preview(template).video)
        self.assertIsNone(read_title_preview(template).image)
        self.assertIsNone(title_preview_kind(template))

    def test_legacy_provider_prefix_is_not_product_branding(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'SC-1-Kinetic Pop In.drb'
            source.write_bytes(b'native')
            template = scan_installed((Path(tmp),))[0]
            self.assertEqual(template.name, 'Kinetic Pop In')
            self.assertEqual(template.locator, str(source.resolve()))

    def test_editorial_rejects_carrier_before_mutating_timeline(self):
        session, pool, proposal = setup()
        unsupported = Template(proposal.templates[0].id, 'Archivo sin base', 'installed_file', 'missing.setting')
        proposal = replace(proposal, templates=(unsupported,))
        writer = EditorialWriter(session.timeline, pool, proposal, {})
        with patch.object(writer, '_get_carrier_media_item') as carrier:
            with self.assertRaisesRegex(EditorialError, 'título nativo'):
                writer.preflight()
        carrier.assert_not_called()
        self.assertEqual(pool.count, 0)
        self.assertEqual(len(session.timeline.names), 1)

    def test_drb_inserts_exact_native_copy_and_keeps_original(self):
        session, pool, proposal = setup()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'Title.drb'
            source.write_bytes(b'native-bin')
            template = replace(scan_installed((Path(tmp),))[0], id=proposal.templates[0].id)
            proposal = replace(proposal, templates=(template,))
            writer = EditorialWriter(session.timeline, pool, proposal, {})
            writer.preflight()
            name = next(iter(writer.assignments))
            with patch('davinci_flow.editorial.writer.import_native_template', return_value=pool.template) as native, \
                 patch.object(writer, '_get_carrier_media_item') as carrier:
                item = writer._insert_fusion_title(2, 86400, 86448, 'Título propio', 'main', None, 24, name)
            self.assertEqual(item.GetTrackTypeAndIndex(), ['video', 2])
            self.assertEqual((item.GetStart(), item.GetDuration()), (86400, 48))
            self.assertEqual(item.comp.tool.value, 'Título propio')
            self.assertEqual(pool.template.comp.tool.value, 'Original')
            native.assert_called_once()
            carrier.assert_not_called()

    def test_native_range_beyond_source_is_rejected_before_append(self):
        session, pool, proposal = setup()
        writer = EditorialWriter(session.timeline, pool, proposal, {})
        media = Mock()
        media.GetClipProperty.return_value = '32'
        with patch.object(pool, 'AppendToTimeline') as append:
            with self.assertRaisesRegex(EditorialError, 'duración suficiente'):
                writer._append_media_item(media, 1, 'video', 2, 86400, 120)
        append.assert_not_called()

    def test_native_template_reuses_bin_and_restores_current_folder(self):
        template = Template('bin_title', 'Native', 'installed_bin', 'Native.drb', fingerprint='a'*64)
        original = Mock()
        folder = Mock()
        folder.GetName.return_value = 'DF_Preset_' + 'a'*20
        folder.GetSubFolderList.return_value = []
        clip = Mock()
        folder.GetClipList.side_effect = [[], [clip], [clip]]
        root = Mock()
        root.GetSubFolderList.return_value = [folder]
        pool = Mock()
        pool.GetRootFolder.return_value = root
        pool.GetCurrentFolder.return_value = original
        pool.SetCurrentFolder.return_value = True
        pool.ImportFolderFromFile.return_value = True
        self.assertIs(import_native_template(pool, template), clip)
        self.assertIs(import_native_template(pool, template), clip)
        pool.ImportFolderFromFile.assert_called_once_with('Native.drb')
        self.assertEqual(pool.SetCurrentFolder.call_args.args, (original,))

    def test_development_data_never_uses_installed_directory(self):
        with patch('davinci_flow.user_data.checkout_root', return_value=Path(__file__).resolve().parents[3]):
            development = user_data_dir()
        with patch('davinci_flow.user_data.checkout_root', return_value=None):
            installed = user_data_dir()
        self.assertNotEqual(development, installed)
        self.assertEqual(development.parent, installed / 'development')


if __name__ == '__main__':
    unittest.main()
