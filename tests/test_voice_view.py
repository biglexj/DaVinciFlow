"""Selección dependiente de motor y voz, sin síntesis real."""

import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from features.voice.voice_view import VoiceView
from test_voice_catalog import catalog


class VoiceSelectorsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        def bind(callback, *args):
            async def handler(event=None):
                result = callback(*args)
                if inspect.isawaitable(result):
                    await result
            return handler
        async def run(message, operation):
            return operation()
        self.access = {'internal': True, 'balance': 0, 'rate': {'rate_credits': 3, 'unit': '100_chars', 'is_active': True},
                       'voices': [{'id': 'gemini-a', 'name': 'Voz A', 'provider': 'gemini'},
                                  {'id': 'gemini-b', 'name': 'Voz B', 'provider': 'gemini'},
                                  {'id': 'other', 'name': 'No habilitada', 'provider': 'minimax'}]}
        self.client = SimpleNamespace(account=SimpleNamespace(user={'id': 'fixture'}),
            access=self.access, pending_id=None, refresh_access=Mock(return_value=self.access),
            generate=Mock(return_value=None))
        app = SimpleNamespace(bind=bind, run=run, navigate=Mock(),
                              page=SimpleNamespace(update=Mock()), notify=Mock())
        self.view = VoiceView(app, self.client)
        self.view.local_loaded = True

    async def test_catalog_is_empty_until_access_returns_available_voices(self):
        self.assertEqual(self.view.engine.options, [])
        self.assertTrue(self.view.engine.disabled)
        self.assertTrue(self.view.voice.disabled)
        await self.view.refresh_access()
        self.assertEqual([option.key for option in self.view.engine.options], ['gemini'])
        self.assertEqual(self.view.engine.value, 'gemini')
        self.assertEqual([option.key for option in self.view.voice.options], ['gemini-a', 'gemini-b'])
        self.view.voice.value = 'gemini-b'
        await self.view.refresh_access()
        self.assertEqual(self.view.voice.value, 'gemini-b')
        self.client.refresh_access.return_value = None
        await self.view.refresh_access()
        self.assertEqual(self.view.engine.options, [])
        self.assertIsNone(self.view.voice.value)
        self.assertTrue(self.view.generate_button.disabled)

    async def test_changing_engine_clears_incompatible_voices_and_blocks_generation(self):
        await self.view.refresh_access()
        self.view.narration.value = 'Mensaje de prueba'
        self.view.engine.value = 'minimax'
        self.view.change_engine()
        self.assertEqual(self.view.voice.options, [])
        self.assertIsNone(self.view.voice.value)
        self.assertTrue(self.view.voice.disabled)
        self.view.generate_button.disabled = False
        await self.view.generate()
        self.client.generate.assert_not_called()

    async def test_generation_uses_the_voice_from_the_selected_engine(self):
        await self.view.refresh_access()
        self.view.narration.value = 'Mensaje de prueba'
        self.view.voice.value = 'gemini-b'
        await self.view.generate()
        self.client.generate.assert_called_once_with('Mensaje de prueba', 'gemini-b', provider='gemini')

    async def test_every_web_engine_filters_voices_and_sends_selected_provider(self):
        self.client.access = catalog()
        self.client.refresh_access.return_value = self.client.access
        await self.view.refresh_access()
        self.assertEqual(len(self.view.engine.options), 5)
        self.view.narration.value = '🎵' * 201
        for provider, cost in [('piper', 4), ('pocket_tts', 12), ('gemini', 9), ('qwen', 18), ('minimax', 9)]:
            self.view.engine.value = provider
            self.view.change_engine()
            self.assertEqual([v.key for v in self.view.voice.options], [provider + '-voice'])
            self.assertIn(f'{cost} créditos', self.view.estimate.value)
            await self.view.generate()
            self.assertEqual(self.client.generate.call_args.kwargs['provider'], provider)
        self.assertEqual(self.client.generate.call_count, 5)

    async def test_local_voices_remain_free_when_cloud_access_is_unavailable(self):
        self.view.local_voices = [{'id': 'local-test', 'name': 'Voz instalada', 'system_name': 'Fixture',
                                   'provider': 'system', 'ready': True}]
        self.client.access = None
        self.client.refresh_access.return_value = None
        self.view.narration.value = 'Prueba de voz local'
        await self.view.refresh_access()
        self.assertEqual(self.view.engine.value, 'system')
        self.assertFalse(self.view.generate_button.disabled)
        self.assertIn('Gratis', self.view.estimate.value)

    async def test_unavailable_engine_is_visible_disabled_and_never_generates(self):
        self.client.access = catalog()
        self.client.access['engines'][4].update(available=False, rate=None, reason='rate-unavailable')
        self.client.refresh_access.return_value = self.client.access
        await self.view.refresh_access()
        option = next(option for option in self.view.engine.options if option.key == 'minimax')
        self.assertTrue(option.disabled)
        self.view.engine.value = 'minimax'
        self.view.narration.value = 'Prueba'
        self.view.change_engine()
        await self.view.generate()
        self.client.generate.assert_not_called()
