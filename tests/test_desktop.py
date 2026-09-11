"""Estado editorial, puente de procesos y ciclo de vida de la nueva interfaz."""

import asyncio
from dataclasses import asdict
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent
SRC_FLET = ROOT / 'src-flet'
if str(SRC_FLET) not in sys.path:
    sys.path.insert(0, str(SRC_FLET))

from davinci_flow.editorial.controller import EditorialController
from davinci_flow.editorial import resolve_bridge
from davinci_flow.editorial.model import EditorialError
try:
    from tests.test_editorial import sample
except ImportError:
    from test_editorial import sample


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.controller = EditorialController(Path(self.temp.name) / 'preferences.json')

    def test_capture_uses_bridge_and_preserves_snapshot_fingerprint(self):
        source = sample()
        with patch.object(resolve_bridge, 'read_resolve', return_value=(source.snapshot, source.templates)) as bridge:
            self.controller.read_resolve(2, 3, 8)
        bridge.assert_called_once_with(2, 3, 8)
        self.assertEqual(self.controller.snapshot.fingerprint, source.snapshot.fingerprint)
        self.assertIn(source.templates[0].id, self.controller.catalog)
        self.assertNotIn(source.templates[0], self.controller.templates)

    def test_failed_capture_and_llm_preserve_review(self):
        original = sample().edit(0, reviewed=True)
        self.controller.proposal = original
        self.controller.snapshot = original.snapshot
        self.controller.dirty = True
        with patch.object(resolve_bridge, 'read_resolve', side_effect=EditorialError('Sin conexión')):
            with self.assertRaises(EditorialError):
                self.controller.read_resolve()
        with patch('davinci_flow.editorial.controller.propose', side_effect=EditorialError('Modelo no disponible')):
            with self.assertRaises(EditorialError):
                self.controller.generate(client=Mock())
        self.assertIs(self.controller.proposal, original)
        self.assertTrue(self.controller.dirty)

    def test_next_template_selection_keeps_saved_proposal_catalog(self):
        self.controller.proposal = sample()
        original_revision = self.controller.proposal.revision
        self.controller.choose_templates({self.controller.templates[0].id})
        self.assertEqual(self.controller.proposal.revision, original_revision)

    def test_missing_resource_selection_is_not_silently_removed(self):
        self.controller.preferences.resource_ids = ['missing']
        self.controller.scan_resources()
        self.assertEqual(self.controller.preferences.resource_ids, ['missing'])
        with self.assertRaisesRegex(EditorialError, 'no están disponibles'):
            self.controller.resource_context()

    def test_resource_context_includes_builtin_sfx_by_default(self):
        resources = self.controller.resource_context()
        categories = {r["category"] for r in resources}
        self.assertIn("sfx", categories)
        ids = {r["id"] for r in resources}
        self.assertIn("sfx_whoosh_clean_01", ids)
        self.assertIn("sfx_pop_subtle_01", ids)

    def test_legacy_load_save_keeps_revision_and_full_caption_mode(self):
        path = Path(self.temp.name) / 'legacy.json'
        sample().save(path)
        self.controller.load_proposal(path)
        self.controller.save_proposal(path)
        self.assertEqual(self.controller.proposal.revision, sample().revision)
        self.assertEqual(self.controller.preferences.mode, 'captions')
        self.assertFalse(self.controller.dirty)

    def test_unreviewed_apply_does_not_start_bridge(self):
        self.controller.proposal = sample()
        with patch.object(resolve_bridge, 'apply') as apply:
            with self.assertRaises(EditorialError):
                self.controller.apply()
            apply.assert_not_called()

    def test_approve_all_marks_proposal_reviewed_and_dirty(self):
        self.controller.proposal = sample()
        self.assertFalse(self.controller.dirty)
        self.assertFalse(self.controller.proposal.decisions[0].reviewed)
        self.controller.approve_all()
        self.assertTrue(self.controller.dirty)
        self.assertTrue(self.controller.proposal.decisions[0].reviewed)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        # Este grupo prueba el transporte CPython de compatibilidad explícito.
        transport = patch.object(resolve_bridge, 'selected_transport', return_value=('legacy', None))
        transport.start()
        self.addCleanup(transport.stop)

    def test_json_transport_restores_snapshot_and_ignores_native_noise(self):
        p = sample()
        data = {'snapshot': asdict(p.snapshot), 'templates': [asdict(t) for t in p.templates]}
        output = 'Native diagnostic\n' + resolve_bridge.RESULT_PREFIX + json.dumps({'ok': True, 'result': data})
        with patch.object(resolve_bridge, 'resolve_python', return_value=sys.executable), \
             patch.object(resolve_bridge.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=output)) as run:
            s, templates = resolve_bridge.read_resolve()
        self.assertEqual(s.fingerprint, p.snapshot.fingerprint)
        self.assertEqual(templates, p.templates)
        self.assertEqual(run.call_args.kwargs['timeout'], 90)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_bridge_fault_is_actionable_and_never_retried(self):
        with patch.object(resolve_bridge, 'resolve_python', return_value=sys.executable), \
             patch.object(resolve_bridge.subprocess, 'run', return_value=SimpleNamespace(returncode=42, stdout='')) as run:
            with self.assertRaisesRegex(EditorialError, 'código 42'):
                resolve_bridge.request('apply', proposal_path='review.json')
        self.assertEqual(run.call_count, 1)
        self.assertIsNone(run.call_args.kwargs['timeout'])

    def test_unknown_operation_never_connects(self):
        with patch('davinci_flow.resolve.connect_to_resolve') as connect:
            with self.assertRaises(EditorialError):
                resolve_bridge.dispatch('evaluate', {'code': 'not allowed'})
            connect.assert_not_called()

    def test_worker_rejects_pypy_before_native_import(self):
        with patch.object(resolve_bridge.platform, 'python_implementation', return_value='PyPy'), \
             patch.object(resolve_bridge, 'dispatch') as dispatch, patch('builtins.print') as output:
            resolve_bridge.main()
        dispatch.assert_not_called()
        self.assertIn('CPython 3.13', output.call_args.args[0])


@unittest.skipUnless(importlib.util.find_spec('flet'), 'Instala el extra desktop para comprobar Flet.')
class DesktopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.app import DesktopApp
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.controller = EditorialController(Path(self.temp.name) / 'prefs.json')
        registry = SimpleNamespace(_services=[])
        registry.register_service = lambda s: registry._services.append(s)
        self.page = SimpleNamespace(window=SimpleNamespace(), services=[], _services=registry,
                                    add=Mock(), update=Mock(), show_dialog=Mock(),
                                    pop_dialog=Mock(), launch_url=Mock())
        self.app = DesktopApp(self.page, self.controller)
        self.addCleanup(self.app.executor.shutdown)

    async def test_routes_keep_same_review_and_errors_centered(self):
        import flet as ft
        self.controller.proposal = sample()
        self.controller.snapshot = sample().snapshot
        await self.app.editor.choose(0)
        self.app.editor.texts['main'].value = 'Edición pendiente'
        await self.app.navigate('catalog')
        await self.app.navigate('editor')
        self.assertTrue(self.app.editor.form_changed())
        self.assertIs(self.app.workspace.content, self.app.editor.content)
        self.app.show_error('Error completo')
        self.assertEqual(self.page.show_dialog.call_args.args[0].alignment, ft.Alignment.CENTER)

    async def test_background_failure_unlocks_ui_and_keeps_proposal(self):
        self.controller.proposal = sample()
        def fail():
            raise EditorialError('Fallo controlado')
        self.assertIsNone(await self.app.run('Trabajando', fail))
        self.assertFalse(self.app.busy)
        self.assertFalse(self.app.body.disabled)
        self.assertIsNotNone(self.controller.proposal)

    async def test_file_picker_filters_files_without_native_service(self):
        from shared.path_picker import list_entries
        root = Path(self.temp.name)
        (root / 'Vídeos').mkdir()
        (root / 'subtítulos.SRT').write_text('', encoding='utf-8')
        (root / 'otro.mp4').write_text('', encoding='utf-8')
        self.assertEqual([p.name for p in list_entries(root, ['srt'])], ['Vídeos', 'subtítulos.SRT'])
        self.assertEqual(len(list_entries(root, directories_only=True)), 1)
        self.assertEqual(self.page.services, [])
        self.assertEqual(self.page._services._services, [])

    async def test_client_wait_uses_sync_process_and_restores_flet_launcher(self):
        import flet_desktop
        from app.runtime import desktop_runtime
        original = flet_desktop.open_flet_view_async
        process = Mock()
        process.wait.return_value = 0
        with patch('app.runtime.platform.python_implementation', return_value='PyPy'), \
             patch('app.runtime.sys.platform', 'win32'), \
             patch.object(flet_desktop, 'open_flet_view', return_value=(process, 'pid')):
            with desktop_runtime():
                wrapped, pid = await flet_desktop.open_flet_view_async('local', None, True)
                self.assertEqual(await wrapped.wait(), 0)
                self.assertEqual(pid, 'pid')
        self.assertIs(flet_desktop.open_flet_view_async, original)

    async def test_centered_picker_opens_selected_srt(self):
        import flet as ft
        target = Path(self.temp.name) / 'subtítulos.srt'
        target.write_text('', encoding='utf-8')
        shown = asyncio.Event()
        self.page.show_dialog.side_effect = lambda dialog: shown.set()
        self.page.pop_dialog = Mock()
        job = asyncio.create_task(self.app.picker.pick_files(initial_directory=self.temp.name, allowed_extensions=['srt']))
        await asyncio.wait_for(shown.wait(), 5)
        dialog = self.page.show_dialog.call_args.args[0]
        self.assertEqual(dialog.alignment, ft.Alignment.CENTER)
        contents = dialog.content.content.controls
        filename_field = [c for c in contents if isinstance(c, ft.TextField)][-1]
        filename_field.value = target.name
        await dialog.actions[1].on_click()
        result = await asyncio.wait_for(job, 2)
        self.assertEqual(Path(result[0].path), target)

    async def test_picker_cancel_keeps_editor_source(self):
        original = sample().snapshot
        self.controller.snapshot = original
        shown = asyncio.Event()
        self.page.show_dialog.side_effect = lambda dialog: shown.set()
        self.page.pop_dialog = Mock()
        job = asyncio.create_task(self.app.picker.get_directory_path(initial_directory=self.temp.name))
        await asyncio.wait_for(shown.wait(), 5)
        await self.page.show_dialog.call_args.args[0].actions[0].on_click()
        self.assertIsNone(await asyncio.wait_for(job, 2))
        self.assertIs(self.controller.snapshot, original)

    async def test_editor_layout_buttons_and_expanded_table(self):
        self.assertTrue(self.app.editor.table_view.expand)
        first_card_row = self.app.editor.content.controls[1].content.controls[0]
        has_cargar_srt = any(getattr(c, 'text', '') == 'Cargar SRT' or getattr(c, 'content', '') == 'Cargar SRT'
                             for c in first_card_row.controls)
        self.assertTrue(has_cargar_srt)
        action_row = self.app.editor.content.controls[4]
        action_labels = [
            getattr(btn, 'text', '') or getattr(btn, 'content', '')
            for sub in action_row.controls
            for btn in (getattr(sub, 'controls', None) or [sub])
        ]
        self.assertIn('Aplicar revisión', action_labels)
        self.assertIn('Deshacer', action_labels)

    async def test_auto_capture_default(self):
        source = sample()
        observed = {}
        def capture(*_):
            observed['loading'] = self.app.editor.initial_loading.visible
            observed['empty'] = self.app.editor.empty.visible
            return source.snapshot, source.templates
        with patch.object(resolve_bridge, 'read_resolve', side_effect=capture):
            await self.app.editor.auto_capture_default()
        self.assertEqual(observed, {'loading': True, 'empty': False})
        self.assertIsNotNone(self.controller.snapshot)
        self.assertEqual(len(self.app.editor.table.rows), len(source.snapshot.cues))
        self.assertFalse(self.app.editor.initial_loading.visible)
        self.assertTrue(self.app.editor.table_view.visible)
        self.assertIn('Subtítulos de Resolve detectados', self.app.status.value)

    async def test_auto_capture_failure_restores_empty_state(self):
        with patch.object(resolve_bridge, 'read_resolve', side_effect=EditorialError('Resolve cerrado')):
            await self.app.editor.auto_capture_default()
        self.assertIsNone(self.controller.snapshot)
        self.assertFalse(self.app.editor.initial_loading.visible)
        self.assertTrue(self.app.editor.empty.visible)
        self.assertEqual(self.app.status.value, 'Listo para abrir tu montaje.')

    async def test_settings_model_selector_and_key_persistence(self):
        from features.settings.settings_view import MASKED_KEY
        settings = self.app.settings
        self.assertIn(self.controller.preferences.model, [opt.key for opt in settings.model_dropdown.options])
        with patch('features.settings.settings_view.has_gemini_api_key', return_value=True):
            settings.refresh()
            self.assertEqual(settings.key.value, MASKED_KEY)
        scanned = ('gemini-3.8-flash', 'gemini-3.7-flash')
        with patch('features.settings.settings_view.list_available_gemini_models', return_value=scanned):
            await settings.scan_models()
            options = [opt.key for opt in settings.model_dropdown.options]
            for m in scanned:
                self.assertIn(m, options)
            self.assertIn('2 modelos detectados', settings.scan_status.value)

    async def test_sidebar_about_button_and_hover(self):
        about_btn = self.app.about_btn
        self.assertIsNotNone(about_btn)
        self.assertEqual(about_btn.tooltip, 'Acerca de DaVinci Flow')
        # Hover activation
        about_btn.on_hover(SimpleNamespace(data='true'))
        self.assertEqual(about_btn.bgcolor, '#173A35')
        self.assertEqual(about_btn.content.controls[0].color, '#00C7B1')
        # Hover deactivation
        about_btn.on_hover(SimpleNamespace(data='false'))
        self.assertIsNone(about_btn.bgcolor)
        self.assertEqual(about_btn.content.controls[0].color, '#ACB7BD')

    async def test_about_dialog_presentation_and_channels(self):
        import flet as ft
        from features.about.about_dialog import (
            DONATIONS_URL, BUY_ME_A_COFFEE_URL, FEEDBACK_URL, GITHUB_URL
        )
        dialog = self.app.show_about()
        self.page.show_dialog.assert_called_with(dialog)
        self.assertIsInstance(dialog, ft.AlertDialog)

        col = dialog.content.content
        buttons_col = col.controls[-1]
        action_buttons = buttons_col.controls
        self.assertEqual(len(action_buttons), 4)

        labels = [str(b.content) for b in action_buttons]
        self.assertTrue(any('Donaciones Oficiales' in l for l in labels))
        self.assertTrue(any('Buy Me a Coffee' in l for l in labels))
        self.assertTrue(any('Feedback' in l for l in labels))
        self.assertTrue(any('GitHub' in l for l in labels))

        # Test launching links
        action_buttons[0].on_click(None)
        self.page.launch_url.assert_called_with(DONATIONS_URL)

        action_buttons[1].on_click(None)
        self.page.launch_url.assert_called_with(BUY_ME_A_COFFEE_URL)

        action_buttons[2].on_click(None)
        self.page.launch_url.assert_called_with(FEEDBACK_URL)

        action_buttons[3].on_click(None)
        self.page.launch_url.assert_called_with(GITHUB_URL)

        # Test update action button in dialog actions
        update_action_btn = dialog.actions[0]
        self.assertIn('Buscar actualizaciones', str(update_action_btn.content))
        with patch.object(self.app, 'check_updates') as mock_check:
            res = update_action_btn.on_click(None)
            if inspect.isawaitable(res):
                await res
            self.assertFalse(dialog.open)
            self.page.pop_dialog.assert_called()
            mock_check.assert_called_with(manual=True)

        # Test dismiss action button
        dismiss_btn = dialog.actions[1]
        self.assertIn('Cerrar', str(dismiss_btn.content))
        dismiss_res = dismiss_btn.on_click(None)
        if inspect.isawaitable(dismiss_res):
            await dismiss_res
        self.page.pop_dialog.assert_called()

    async def test_settings_updater_panel_layout_and_interactions(self):
        from davinci_flow.updater.checker import UpdateRelease
        settings = self.app.settings
        self.assertIsNotNone(settings.col_left)
        self.assertIsNotNone(settings.col_right)
        self.assertEqual(settings.col_left.expand, 1)
        self.assertEqual(settings.col_right.expand, 1)
        self.assertIsNotNone(settings.updater_card)
        self.assertIsNotNone(settings.update_status_chip)
        self.assertIsNotNone(settings.check_button)
        self.assertIsNotNone(settings.update_content_box)

        # Estado inicial
        self.assertIn('Comprobación pendiente', settings.update_status_chip.content.value)

        # 1. Comprobación manual sin versión nueva
        with patch('davinci_flow.updater.checker.check_github_release', return_value=None):
            await self.app.check_updates(manual=True)
            self.assertEqual(settings.update_status_chip.content.value, 'Al día')
            self.assertIn('Estás en la última versión', self.app.toast_text.value)

        # 2. Comprobación con actualización detectada
        mock_release = UpdateRelease(
            version='0.3.1',
            download_url='https://github.com/biglexj/DaVinciFlow/releases/download/v0.3.1/setup.exe',
            release_page_url='https://github.com/biglexj/DaVinciFlow/releases/tag/v0.3.1',
            body='## Novedades\n- Soporte para nuevos motores Fusion.\n- Correcciones menores.',
            published_at='2026-09-08T12:00:00Z',
            is_newer=True,
            sanitized_notes='Novedades:\n• Soporte para nuevos motores Fusion.\n• Correcciones menores.',
        )
        with patch('davinci_flow.updater.checker.check_github_release', return_value=mock_release):
            await self.app.check_updates(manual=True)
            self.assertEqual(settings.update_status_chip.content.value, 'Nueva v0.3.1')
            self.assertIsNotNone(settings.update_content_box.content)

    async def test_show_toast_overlay(self):
        await self.app.show_toast('Toast de prueba', duration=0.02)
        self.assertEqual(self.app.toast_text.value, 'Toast de prueba')
        self.assertEqual(self.app.toast_overlay.opacity, 1.0)
        await asyncio.sleep(0.06)
        self.assertEqual(self.app.toast_overlay.opacity, 0.0)

    async def test_editor_review_card_close_and_toggle(self):
        self.controller.proposal = sample()
        self.controller.snapshot = self.controller.proposal.snapshot
        self.app.editor.refresh()
        self.assertFalse(self.app.editor.review_card.visible)
        self.assertIsNone(self.app.editor.selected)

        # Abrir revisión del bloque 0
        await self.app.editor.choose(0)
        self.assertTrue(self.app.editor.review_card.visible)
        self.assertEqual(self.app.editor.selected, 0)

        # Cerrar revisión directamente
        await self.app.editor.close_review()
        self.assertFalse(self.app.editor.review_card.visible)
        self.assertIsNone(self.app.editor.selected)

        # Alternar pulsando dos veces la misma fila
        await self.app.editor.choose(0)
        self.assertTrue(self.app.editor.review_card.visible)
        await self.app.editor.choose(0)
        self.assertFalse(self.app.editor.review_card.visible)
        self.assertIsNone(self.app.editor.selected)

    async def test_editor_approve_all_and_apply_flow(self):
        self.controller.proposal = sample()
        self.controller.snapshot = self.controller.proposal.snapshot
        self.app.editor.refresh()
        self.assertFalse(self.controller.proposal.decisions[0].reviewed)

        # Botón Aprobar todo
        await self.app.editor.approve_all()
        self.assertTrue(self.controller.proposal.decisions[0].reviewed)
        self.assertIn('1/1 revisados', self.app.editor.count.value)

        # Aplicar cuando ya está todo revisado
        with patch.object(self.controller, 'apply', return_value=SimpleNamespace(item_count=1)):
            await self.app.editor.apply()
            self.assertIn('Aplicados 1 elementos', self.app.status.value)

    async def test_editor_apply_prompts_bulk_approval_when_unreviewed(self):
        self.controller.proposal = sample()
        self.controller.snapshot = self.controller.proposal.snapshot
        self.app.editor.refresh()
        self.assertFalse(self.controller.proposal.decisions[0].reviewed)

        # Caso 1: el usuario cancela en el diálogo -> no se aprueba ni se aplica
        with patch.object(self.app, 'confirm', return_value=False) as mock_confirm, \
             patch.object(self.controller, 'apply') as mock_apply:
            await self.app.editor.apply()
            mock_confirm.assert_called_once()
            mock_apply.assert_not_called()
            self.assertFalse(self.controller.proposal.decisions[0].reviewed)

        # Caso 2: el usuario acepta en el diálogo -> aprueba todo y aplica
        with patch.object(self.app, 'confirm', return_value=True) as mock_confirm, \
             patch.object(self.controller, 'apply', return_value=SimpleNamespace(item_count=1)) as mock_apply:
            await self.app.editor.apply()
            mock_confirm.assert_called_once()
            mock_apply.assert_called_once()
            self.assertTrue(self.controller.proposal.decisions[0].reviewed)

    async def test_path_picker_drives_and_new_folder(self):
        from shared.path_picker import get_system_drives
        drives = get_system_drives()
        self.assertTrue(len(drives) >= 1)

        shown = asyncio.Event()
        self.page.show_dialog.side_effect = lambda dialog: shown.set()
        self.page.pop_dialog = Mock()

        target_dir = Path(self.temp.name) / 'subdir'
        target_dir.mkdir()

        job = asyncio.create_task(self.app.picker.save_file(
            dialog_title='Guardar prueba',
            initial_directory=str(target_dir),
            file_name='test.json'
        ))
        await asyncio.wait_for(shown.wait(), 5)
        dialog = self.page.show_dialog.call_args.args[0]
        col = dialog.content.content
        nav_row = col.controls[0]
        new_folder_box = col.controls[1]
        new_folder_field = new_folder_box.content.controls[0]
        create_btn = new_folder_box.content.controls[1]

        # Desplegar caja de nueva carpeta
        folder_btn = nav_row.controls[2]
        await folder_btn.on_click(None)
        self.assertTrue(new_folder_box.visible)

        # Crear carpeta nueva
        new_folder_field.value = 'nueva_carpeta'
        await create_btn.on_click(None)
        self.assertTrue((target_dir / 'nueva_carpeta').is_dir())

        # Cancelar diálogo
        await dialog.actions[0].on_click(None)
        self.assertIsNone(await asyncio.wait_for(job, 2))


class InstanceTests(unittest.TestCase):
    def test_second_process_activates_first_then_releases_lock(self):
        from app.instance import DesktopInstance
        with tempfile.TemporaryDirectory() as tmp:
            first = DesktopInstance(tmp)
            self.assertTrue(first.acquire())
            try:
                import os
                env = os.environ.copy()
                env['PYTHONPATH'] = str(SRC_FLET) + os.pathsep + env.get('PYTHONPATH', '')
                result = subprocess.run([sys.executable, '-c',
                    'from app.instance import DesktopInstance; import sys; '
                    'i=DesktopInstance(sys.argv[1]); print(i.acquire()); i.release()', tmp],
                    capture_output=True, text=True, timeout=15, env=env)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), 'False')
                self.assertTrue(first.activation_requested())
                self.assertFalse(first.activation_requested())
            finally:
                first.release()
            second = DesktopInstance(tmp)
            self.assertTrue(second.acquire())
            second.release()
