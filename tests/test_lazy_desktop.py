"""Regresiones de carga por demanda y lectura de medios fuera de la interfaz."""

import asyncio
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.app import DesktopApp
from davinci_flow.editorial.controller import EditorialController
from davinci_flow.assets.library import Resource


class LazyDesktopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.controller = EditorialController(Path(self.temp.name) / 'prefs.json')
        registry = SimpleNamespace(_services=[])
        registry.register_service = lambda service: registry._services.append(service)
        self.page = SimpleNamespace(window=SimpleNamespace(), services=[], _services=registry,
            add=Mock(), update=Mock(), show_dialog=Mock(), pop_dialog=Mock(), launch_url=Mock())
        self.app = DesktopApp(self.page, self.controller)
        self.addCleanup(self.app.executor.shutdown)
        self.addCleanup(self.app.media_executor.shutdown)

    async def test_startup_and_background_checks_do_not_open_unused_views(self):
        self.assertEqual(set(self.app.views.loaded), {'editor'})
        self.assertIn('sfx', self.app.views)
        self.app.refresh_identity()
        with patch('app.app.user_data_dir', return_value=Path(self.temp.name)):
            await self.app.poll_voice_callback()
        with patch('davinci_flow.updater.checker.check_github_release', return_value=None):
            await self.app.check_updates()
        self.assertEqual(set(self.app.views.loaded), {'editor'})
        self.assertIs(self.app.sfx, self.app.views['sfx'])
        self.assertEqual(set(self.app.views.loaded), {'editor', 'sfx'})

    async def test_pending_login_still_loads_voice_on_demand(self):
        root = Path(self.temp.name)
        (root / 'account').mkdir()
        (root / 'account' / 'callback.bin').touch()
        voice = SimpleNamespace(handle_callback_if_ready=unittest.mock.AsyncMock())
        with patch('app.app.user_data_dir', return_value=root), \
             patch('features.voice.voice_view.VoiceView', return_value=voice) as factory:
            await self.app.poll_voice_callback()
            await self.app.poll_voice_callback()
        factory.assert_called_once()
        self.assertEqual(voice.handle_callback_if_ready.await_count, 2)

    async def test_sfx_scan_runs_in_worker_and_is_reused_until_reindex(self):
        view = self.app.sfx
        threads = []
        def scan(raw):
            threads.append(threading.current_thread().name)
            return [], {}
        with patch.object(view, '_scan_sounds', side_effect=scan) as scanner:
            await self.app.navigate('sfx')
            await self.app.navigate('editor')
            await self.app.navigate('sfx')
            self.assertEqual(scanner.call_count, 1)
            await view.reindex()
            self.assertEqual(scanner.call_count, 2)
            self.controller.preferences.paths['sfx'] = self.temp.name
            await view.open()
            self.assertEqual(scanner.call_count, 3)
        self.assertTrue(all(name.startswith('flow-media') for name in threads))

    async def test_broll_scan_is_deferred_and_cached_by_page(self):
        clip = Path(self.temp.name) / 'video.mp4'
        clip.write_bytes(b'fixture')
        view = self.app.brolls
        self.assertEqual(view.list_column.controls, [])
        with patch.object(view, '_collect_files', return_value=(clip,)) as scanner:
            await self.app.navigate('brolls')
            await self.app.navigate('editor')
            await self.app.navigate('brolls')
            self.assertEqual(scanner.call_count, 1)
            await view.open(force=True)
            self.assertEqual(scanner.call_count, 2)

    async def test_music_reads_art_only_for_visible_page_and_reuses_it(self):
        self.controller.resources = tuple(Resource(str(i), 'music', f'song{i}.mp3', f'missing{i}.mp3')
                                          for i in range(100))
        self.app.current = 'music'
        with patch('features.library.library_view.cover_art', return_value=None) as art:
            view = self.app.music
            art.assert_not_called()
            visible = self.controller.resources[:view.page_size]
            await view._hydrate_art(visible, view.art_generation)
            self.assertEqual(art.call_count, 48)
            await view.toggle('0')
            await view._hydrate_art(visible, view.art_generation)
            self.assertEqual(art.call_count, 48)
            await view.paginate(1)
            await view._hydrate_art(self.controller.resources[48:96], view.art_generation)
            self.assertEqual(art.call_count, 96)
            self.assertNotIn('99', view.art_loaded)

    async def test_leaving_music_discards_pending_thumbnail_without_reading_more(self):
        self.app.current = 'music'
        self.controller.resources = tuple(Resource(str(i), 'music', 'song.mp3', 'missing.mp3') for i in range(3))
        view = self.app.music
        started, release = threading.Event(), threading.Event()
        def slow_art(resource):
            started.set()
            release.wait(2)
            return b'fixture', 'image/jpeg'
        with patch.object(view, '_art', side_effect=slow_art) as art:
            job = asyncio.create_task(view._hydrate_art(self.controller.resources, view.art_generation))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                self.app.current = 'editor'
            finally:
                release.set()
            await asyncio.wait_for(job, 3)
        self.assertEqual(art.call_count, 1)
        self.assertEqual(view.art_loaded, set())
