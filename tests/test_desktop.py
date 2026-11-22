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
        self.addCleanup(self.app.media_executor.shutdown)

    async def test_voice_import_is_explicit_and_failed_import_preserves_selected_audio(self):
        from unittest.mock import AsyncMock
        audio = Path(self.temp.name) / 'Voice Studio.wav'
        audio.write_bytes(b'generated-audio')
        self.app.pick_file = AsyncMock(return_value=str(audio))
        with patch('features.voice.voice_view.import_voice_file', side_effect=EditorialError('Sin conexión')) as importer:
            await self.app.voice.pick_audio()
            importer.assert_not_called()
            self.assertFalse(self.app.voice.import_button.disabled)
            await self.app.voice.import_audio()
        importer.assert_called_once_with(audio.resolve())
        self.assertEqual(self.app.voice.audio_path, audio.resolve())
        self.assertEqual(audio.read_bytes(), b'generated-audio')

    async def test_voice_studio_opens_canonical_web_route_and_awaits_launcher(self):
        from unittest.mock import AsyncMock
        self.page.launch_url = AsyncMock()
        await self.app.voice.open_studio()
        self.page.launch_url.assert_awaited_once_with('https://biglexj.com/creator-suite/audio?tab=voice_studio')

    async def test_voice_logout_clears_private_draft_and_selection(self):
        self.app.voice.narration.value = 'Guion privado de la cuenta anterior'
        self.app.voice.voice.value = 'old-voice'
        self.app.voice.client = SimpleNamespace(account=SimpleNamespace(user=None), access=None, pending_id=None, logout=Mock(return_value=True))
        await self.app.voice.logout()
        self.assertEqual(self.app.voice.narration.value, '')
        self.assertIsNone(self.app.voice.voice.value)
        self.assertEqual(self.app.voice.voice.options, [])
        self.assertIsNone(self.app.voice.engine.value)
        self.assertEqual(self.app.voice.engine.options, [])
        self.assertTrue(self.app.voice.engine.disabled)
        self.assertTrue(self.app.voice.import_button.disabled)

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

    async def test_opening_catalog_loads_animation_previews_once_after_restart(self):
        from davinci_flow.editorial.model import Template
        source = Path(self.temp.name) / 'Kinetic Pop In.drb'
        source.write_bytes(b'bin')
        source.with_suffix('.mp4').write_bytes(b'original-preview')
        template = Template('local_animation', 'Kinetic Pop In', 'installed_bin', str(source))
        def scan():
            self.controller.catalog[template.id] = template
            return 1, []
        with patch.object(self.controller, 'scan_titles', side_effect=scan) as scanner:
            await self.app.navigate('catalog')
            self.assertEqual(self.app.catalog.source.value, 'all')
            self.assertIn(template.id, self.app.catalog.grid_images)
            await self.app.navigate('editor')
            await self.app.navigate('catalog')
        scanner.assert_called_once()
        self.assertIs(self.app.workspace.content, self.app.catalog.content)

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

    async def test_dismissing_picker_or_confirmation_resolves_as_cancelled(self):
        shown = asyncio.Event()
        self.page.show_dialog.side_effect = lambda dialog: shown.set()
        for operation, expected in (
            (self.app.picker.get_directory_path(initial_directory=self.temp.name), None),
            (self.app.confirm('Reemplazar archivo', '¿Deseas reemplazarlo?'), False),
        ):
            shown.clear()
            job = asyncio.create_task(operation)
            await asyncio.wait_for(shown.wait(), 5)
            dialog = self.page.show_dialog.call_args.args[0]
            self.assertFalse(dialog.modal)
            await dialog.on_dismiss(None)
            self.assertIs(await asyncio.wait_for(job, 2), expected)
        self.page.pop_dialog.assert_not_called()

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
        generation_row = self.app.editor.content.controls[3]
        generation_labels = [
            getattr(btn, 'text', '') or getattr(btn, 'content', '')
            for sub in generation_row.controls
            for btn in (getattr(sub, 'controls', None) or [sub])
        ]
        self.assertIn('Generar tanda', generation_labels)
        self.assertIn('Decisiones', generation_labels)

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

    async def test_settings_gemini_requires_a_key_before_showing_models(self):
        settings = self.app.settings
        with patch('features.settings.settings_view.has_gemini_api_key', return_value=False), \
                patch('features.settings.settings_view.list_available_gemini_model_info') as scan:
            settings.refresh()
            await settings.scan_models()
        self.assertEqual(settings.model_dropdown.options, [])
        self.assertIsNone(settings.model_dropdown.value)
        self.assertTrue(settings.model_dropdown.disabled)
        self.assertEqual(settings.key_status.value, 'Ingresa tu clave API de Gemini.')
        scan.assert_not_called()

    async def test_settings_model_selector_and_key_persistence(self):
        from features.settings.settings_view import MASKED_KEY
        from davinci_flow.ai.client import GeminiModelInfo
        settings = self.app.settings
        self.controller.preferences.long_context_enabled = True
        current = self.controller.preferences.model
        scanned = [
            GeminiModelInfo(current, 1000000, 8192, True),
            GeminiModelInfo('gemini-4-argon', 1000000, 8192, True),
            GeminiModelInfo('gemini-4-carbon', None, 8192, True),
        ]
        with patch('features.settings.settings_view.has_gemini_api_key', return_value=True), \
                patch('features.settings.settings_view.list_available_gemini_model_info', side_effect=[scanned, ()]) as scan:
            settings.refresh()
            self.assertEqual(settings.key.value, MASKED_KEY)
            self.assertEqual(settings.model_dropdown.options, [])
            await settings.scan_models()
            options = [info.model_id for info in scanned]
            self.assertEqual([opt.key for opt in settings.model_dropdown.options], options)
            self.assertEqual([opt.text for opt in settings.model_dropdown.options], options)
            self.assertIn('3 modelos disponibles', settings.scan_status.value)
            self.assertEqual(settings.model_dropdown.value, current)
            scan.assert_called_once_with(use_fallback=False)
            await settings.scan_models()
            self.assertEqual([opt.key for opt in settings.model_dropdown.options], options)
            self.assertIn('No se pudo confirmar el catálogo', settings.scan_status.value)
        self.controller.preferences.model = 'gemini-4-carbon'
        self.assertFalse(self.app.editor._batch_generator_args()[3])

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
        support_row = next(c for c in col.controls if isinstance(c, ft.ResponsiveRow))
        support_buttons = [c.content for c in support_row.controls]
        links_row = next(
            c for c in col.controls
            if isinstance(c, ft.Row) and any(isinstance(btn, ft.OutlinedButton) for btn in c.controls)
        )
        link_buttons = list(links_row.controls)
        self.assertEqual(len(support_buttons), 2)
        self.assertEqual(len(link_buttons), 4)

        github_btn = next(b for b in link_buttons if getattr(b, 'content', '') == '@biglexj')
        feedback_btn = next(b for b in link_buttons if getattr(b, 'content', '') == 'Reportar un problema')

        # Test launching links for the 4 canonical support channels
        await support_buttons[0].on_click(None)
        self.page.launch_url.assert_called_with(DONATIONS_URL)

        await support_buttons[1].on_click(None)
        self.page.launch_url.assert_called_with(BUY_ME_A_COFFEE_URL)

        await feedback_btn.on_click(None)
        self.page.launch_url.assert_called_with(FEEDBACK_URL)

        await github_btn.on_click(None)
        self.page.launch_url.assert_called_with(GITHUB_URL)

        # El panel consulta y muestra el resultado dentro del mismo diálogo.
        self.assertTrue(any(control is self.app.updates.content for control in col.controls))
        update_action_btn = self.app.updates.check_button
        self.assertIn('Buscar actualizaciones', str(update_action_btn.content))
        with patch.object(self.app, 'check_updates') as mock_check:
            res = update_action_btn.on_click(None)
            if inspect.isawaitable(res):
                await res
            self.page.pop_dialog.assert_not_called()
            mock_check.assert_called_with(manual=True)

        # Test dismiss action button
        dismiss_btn = dialog.actions[0]
        self.assertIn('Cerrar', str(dismiss_btn.content))
        dismiss_res = dismiss_btn.on_click(None)
        if inspect.isawaitable(dismiss_res):
            await dismiss_res
        self.page.pop_dialog.assert_called()

    async def test_updates_remain_in_about_and_report_unverified_result(self):
        from dataclasses import replace
        from davinci_flow.updater.checker import UpdateRelease
        panel = self.app.updates
        initial_view = self.app.current

        # Estado inicial
        self.assertIn('Comprobación pendiente', panel.update_status_chip.content.value)

        # Una consulta sin respuesta verificable no acredita estar al día.
        with patch('davinci_flow.updater.checker.check_github_release', return_value=None):
            await self.app.check_updates(manual=True)
            self.assertEqual(panel.update_status_chip.content.value, 'Sin confirmar')

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
        with patch('davinci_flow.updater.checker.check_github_release', return_value=replace(mock_release, is_newer=False)):
            await self.app.check_updates(manual=True)
            self.assertEqual(panel.update_status_chip.content.value, 'Al día')
        with patch('davinci_flow.updater.checker.check_github_release', return_value=mock_release):
            await self.app.check_updates(manual=True)
            self.assertEqual(panel.update_status_chip.content.value, 'Nueva v0.3.1')
            self.assertIsNotNone(panel.update_content_box.content)
            self.assertEqual(self.app.current, initial_view)

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

    async def test_library_is_the_last_entry_before_settings(self):
        order = list(self.app.labels)
        self.assertEqual(order[-2:], ['library', 'settings'])
        self.assertLess(order.index('fetch'), order.index('library'))

    async def test_library_tabs_use_short_names(self):
        labels = [str(control.content) for control in self.app.library.category_buttons.values()]
        self.assertEqual(labels, ['B-rolls', 'Efectos (SFX)', 'Música', 'Títulos y Fusion', 'Textos y documentos'])

    async def test_music_category_shows_cover_art_in_square_tiles(self):
        from davinci_flow.assets.library import Resource
        try:
            from tests.test_cover_art import JPEG, _id3_apic
        except ImportError:
            from test_cover_art import JPEG, _id3_apic
        song = Path(self.temp.name) / 'tema.mp3'
        song.write_bytes(_id3_apic())
        self.controller.resources = (Resource('id-musica', 'music', 'tema.mp3', str(song)),)
        self.app.music.refresh()
        self.app.current = 'music'
        await self.app.music._hydrate_art(self.controller.resources, self.app.music.art_generation)
        self.assertFalse(self.app.music.list.visible)
        self.assertTrue(self.app.music.grid.visible)
        self.assertEqual(self.app.music.grid.child_aspect_ratio, 1.0)
        tiles = self.app.music.grid.controls
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0].content.controls[0].content.src, JPEG)
        await self.app.music.toggle('id-musica')
        self.assertIn('id-musica', self.controller.preferences.resource_ids)
        self.assertTrue(self.app.music.tiles['id-musica'][1].visible)

    async def test_music_playback_does_not_select_for_ai_and_stops_on_navigation(self):
        from unittest.mock import AsyncMock
        import flet as ft
        import flet_video as ftv
        from davinci_flow.assets.library import Resource
        song = Path(self.temp.name) / 'tema.wav'
        song.write_bytes(b'audio-fixture')
        self.controller.resources = (Resource('song', 'music', song.name, str(song)),)
        self.app.current = 'music'
        selected = list(self.controller.preferences.resource_ids)
        with patch.object(ftv.Video, 'pause', new_callable=AsyncMock) as pause, \
                patch.object(ftv.Video, 'play', new_callable=AsyncMock) as play:
            await self.app.music.play_audio('song')
            self.assertEqual(self.controller.preferences.resource_ids, selected)
            self.assertTrue(self.app.music.is_playing)
            self.assertEqual(self.app.music.tiles['song'][2].icon, ft.Icons.PAUSE_ROUNDED)
            self.assertEqual(self.app.music.player.playlist[0].resource, song.as_uri())
            self.assertFalse(self.app.music.player.configuration.enable_hardware_acceleration)
            self.assertEqual(self.app.music.player.configuration.hardware_decoding_api, 'no')
            self.app.music._audio_complete(SimpleNamespace(control=self.app.music.player, data=False))
            self.assertTrue(self.app.music.is_playing)
            await self.app.music.play_audio('song')
            self.assertFalse(self.app.music.is_playing)
            await self.app.music.play_audio('song')
            play.assert_awaited_once()
            await self.app.navigate('editor')
        self.assertEqual(pause.await_count, 2)
        self.assertIsNone(self.app.music.player)
        self.assertIsNone(self.app.music.player_host.content)

    async def test_brolls_category_uses_grid_and_sidecar_poster(self):
        from davinci_flow.assets.library import Resource
        try:
            from tests.test_cover_art import JPEG
        except ImportError:
            from test_cover_art import JPEG
        clip = Path(self.temp.name) / 'clip.mp4'
        clip.write_bytes(b'video')
        (Path(self.temp.name) / 'clip.jpg').write_bytes(JPEG)
        self.controller.resources = (Resource('id-broll', 'visuals', 'clip.mp4', str(clip)),)
        self.controller.preferences.paths['visuals'] = self.temp.name
        self.app.brolls.refresh()
        tiles = [tile for tile in self.app.brolls.list_column.controls if tile.tooltip == str(clip)]
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0].content.controls[0].content.src, str(clip.with_suffix('.jpg')))

    async def test_video_preview_stays_in_tile_and_stops_on_navigation(self):
        from unittest.mock import AsyncMock
        import flet as ft
        import flet_video as ftv
        from davinci_flow.assets.library import Resource
        clip = Path(self.temp.name) / 'clip.mp4'
        clip.write_bytes(b'video-fixture')
        self.controller.resources = (Resource('clip', 'visuals', clip.name, str(clip)),)
        self.controller.preferences.paths['visuals'] = self.temp.name
        self.app.current = 'brolls'
        view = self.app.brolls
        view.refresh()
        tile = view.list_column.controls[0]
        play_button = tile.content.controls[-1].content
        self.assertIs(tile.on_click, play_button.on_click)
        host = tile.content.controls[0]
        poster = host.content
        selected = list(self.controller.preferences.resource_ids)
        with patch.object(ftv.Video, 'pause', new_callable=AsyncMock) as pause, \
             patch.object(ftv.Video, 'play', new_callable=AsyncMock) as play:
            await tile.on_click(None)
            player = view.video_preview.player
            self.assertIs(host.content, player)
            self.assertEqual(player.playlist[0].resource, clip.as_uri())
            self.assertEqual(player.fit, ft.BoxFit.CONTAIN)
            self.assertFalse(player.configuration.enable_hardware_acceleration)
            self.assertEqual(player.configuration.hardware_decoding_api, 'no')
            self.assertEqual(view.list_column.child_aspect_ratio, 16/9)
            self.assertEqual(selected, self.controller.preferences.resource_ids)
            view.video_preview._complete(SimpleNamespace(control=player, data=False))
            self.assertIs(host.content, player)
            await play_button.on_click(None)
            self.assertFalse(view.video_preview.is_playing)
            await play_button.on_click(None)
            play.assert_awaited_once()
            await self.app.navigate('editor')
        self.assertEqual(pause.await_count, 2)
        self.assertIs(host.content, poster)
        self.assertEqual(play_button.icon, ft.Icons.PLAY_ARROW_ROUNDED)
        self.assertIsNone(view.video_preview.player)

    async def test_library_only_manages_folders_and_music_links_to_its_category(self):
        from davinci_flow.assets.library import Resource
        self.controller.resources = (Resource('song', 'music', 'tema.mp3', 'missing.mp3'),)
        with patch('features.library.library_view.cover_art') as read_cover:
            await self.app.library.change_category('music')
            read_cover.assert_not_called()
        view = self.app.library
        self.assertTrue(view.manage_only)
        self.assertFalse(view.grid.visible)
        self.assertFalse(view.list.visible)
        self.assertEqual(view.tiles, {})
        self.assertIn(view.folders_card, view.content.controls)
        self.assertNotIn(view.query, view.content.controls)
        self.assertNotIn(self.app.music.folders_card, self.app.music.content.controls)
        await self.app.library.change_category('visuals')
        await self.app.music.manage_folders()
        self.assertEqual(self.app.current, 'library')
        self.assertEqual(self.app.library.category, 'music')
        self.assertIn('1 recursos indexados', self.app.library.summary.value)

    async def test_broll_preview_switches_tiles_and_search_stops_video(self):
        from unittest.mock import AsyncMock
        import flet as ft
        import flet_video as ftv
        view = self.app.brolls
        self.controller.preferences.paths['visuals'] = self.temp.name
        for name in ('a.mp4', 'b.mp4'):
            (Path(self.temp.name) / name).write_bytes(b'video-fixture')
        view.refresh()
        first, second = view.list_column.controls
        host1, host2 = first.content.controls[0], second.content.controls[0]
        poster1, poster2 = host1.content, host2.content
        button1, button2 = first.content.controls[-1].content, second.content.controls[-1].content
        with patch.object(ftv.Video, 'pause', new_callable=AsyncMock) as pause:
            await button1.on_click(None)
            old_player = view.video_preview.player
            await button2.on_click(None)
            self.assertIs(host1.content, poster1)
            self.assertEqual(button1.icon, ft.Icons.PLAY_ARROW_ROUNDED)
            self.assertIs(host2.content, view.video_preview.player)
            view.video_preview._complete(SimpleNamespace(control=old_player, data=True))
            self.assertIs(host2.content, view.video_preview.player)
            view.query.value = 'b'
            await view.search()
        self.assertEqual(pause.await_count, 2)
        self.assertIs(host2.content, poster2)
        self.assertIsNone(view.video_preview.player)

    async def test_broll_pages_fill_grid_without_repeating_or_hiding_remaining_files(self):
        view = self.app.brolls
        root = Path(self.temp.name)
        self.controller.preferences.paths['visuals'] = str(root)
        for i in range(70):
            (root / f'clip-{i:03}.mp4').write_bytes(b'video')
        (root / 'subfolder').mkdir()
        (root / 'subfolder' / 'nested.mp4').write_bytes(b'video')
        view.refresh()
        first = {tile.tooltip for tile in view.list_column.controls}
        self.assertEqual(len(first), 48)
        self.assertTrue(view.has_next)
        await view.paginate(1)
        second = {tile.tooltip for tile in view.list_column.controls}
        self.assertEqual(len(second), 22)
        self.assertFalse(first & second)
        self.assertFalse(view.has_next)
        await view.paginate(1)
        self.assertEqual(view.offset, 48)
        view.query.value = 'nested'
        await view.search()
        self.assertEqual(view.offset, 0)
        self.assertEqual(len(view.list_column.controls), 1)
        self.assertEqual(view.list_column.controls[0].tooltip, str(root / 'subfolder' / 'nested.mp4'))

    async def test_all_views_flutter_layout_safety(self):
        """Verifica que ninguna vista contenga un hijo con expand=True dentro de un Row(wrap=True),
        lo cual provoca una excepción de RenderFlex y una pantalla gris sólida en Flutter."""
        import flet as ft
        def check_control(ctrl, path):
            if isinstance(ctrl, ft.Row) and getattr(ctrl, 'wrap', False):
                for i, child in enumerate(ctrl.controls):
                    self.assertFalse(
                        getattr(child, 'expand', False),
                        f"Control {child} en {path} tiene expand=True dentro de un Row con wrap=True."
                    )
            children = getattr(ctrl, 'controls', None)
            if children:
                for i, c in enumerate(children):
                    check_control(c, f"{path}.controls[{i}]")
            inner = getattr(ctrl, 'content', None)
            if inner:
                check_control(inner, f"{path}.content")

        for name, view in self.app.views.items():
            check_control(view.content, name)


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
