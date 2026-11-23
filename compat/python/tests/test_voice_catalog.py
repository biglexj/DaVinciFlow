import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from davinci_flow.voice.aurora import AuroraVoiceClient
from davinci_flow.voice.aurora_http import AuroraError
from davinci_flow.voice.catalog import normalize_catalog, voice_cost
from test_aurora_voice import UID, wave_bytes


def catalog(internal=False):
    definitions = [('piper', 2, '200_chars'), ('pocket_tts', 4, '100_chars'), ('gemini', 3, '100_chars'),
                   ('qwen', 6, '100_chars'), ('minimax', 3, '100_chars')]
    engines = [{'id': key, 'name': key, 'available': True,
                'rate': {'rate_credits': rate, 'unit': unit, 'is_active': True}} for key, rate, unit in definitions]
    return {'catalog_version': 2, 'user': {'id': UID}, 'internal': internal, 'trial': not internal,
            'plan': 'Prueba', 'balance': 100, 'rate': engines[2]['rate'], 'engines': engines,
            'voices': [{'id': key + '-voice', 'name': key + ' voice', 'provider': key, 'ready': True}
                       for key, _, _ in definitions]}


class MultiProviderVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.account = SimpleNamespace(user={'id': UID}, token=Mock(return_value='fixture-token'),
            invalidate=Mock(), refresh_profile_avatar=Mock())
        self.client = AuroraVoiceClient(self.account, Path(self.temp.name))

    def test_access_accepts_all_engines_without_adding_or_changing_voices(self):
        value = catalog()
        with patch('davinci_flow.voice.aurora.json_request', return_value=value):
            access = self.client.refresh_access()
        self.assertEqual({engine['id'] for engine in access['engines']}, {'piper', 'pocket_tts', 'gemini', 'qwen', 'minimax'})
        self.assertEqual(len(access['voices']), 5)
        invalid = copy.deepcopy(value)
        invalid['engines'][0]['rate']['unit'] = 'wrong'
        with self.assertRaises(AuroraError):
            normalize_catalog(invalid)
        invalid['engines'][0]['available'] = False
        self.assertFalse(normalize_catalog(invalid)['engines'][0]['available'])

    def test_each_provider_preserves_identity_rate_audio_and_pending_metadata(self):
        expected = {'piper': 4, 'pocket_tts': 12, 'gemini': 9, 'qwen': 18, 'minimax': 9}
        for provider, cost in expected.items():
            with self.subTest(provider=provider):
                self.client.access = normalize_catalog(catalog())
                def response(method, url, payload, **kwargs):
                    self.assertEqual(payload['provider'], provider)
                    self.assertEqual(payload['voice_id'], provider + '-voice')
                    self.assertEqual(payload['max_cost'], cost)
                    self.assertEqual(kwargs['timeout'], 3615 if provider == 'qwen' else 210)
                    self.assertEqual(self.client.pending_provider, provider)
                    return 200, {'content-type': 'audio/wav', 'x-voice-provider': provider,
                        'x-voice-id': provider + '-voice', 'x-request-id': self.client.pending_id,
                        'x-cost-credits': str(cost)}, wave_bytes()
                with patch('davinci_flow.voice.aurora.request', side_effect=response):
                    path = self.client.generate('🎵' * 201, provider + '-voice', provider=provider)
                self.assertEqual(path.read_bytes(), wave_bytes())
                self.assertIsNone(self.client.pending_id)

    def test_uncertain_qwen_result_survives_restart_without_new_synthesis(self):
        self.client.access = normalize_catalog(catalog())
        with patch('davinci_flow.voice.aurora.request', side_effect=AuroraError(0, 'network')):
            with self.assertRaises(AuroraError):
                self.client.generate('Prueba', 'qwen-voice', provider='qwen')
        identifier = self.client.pending_id
        recovered = AuroraVoiceClient(self.account, Path(self.temp.name))
        result = 200, {'content-type': 'audio/wav', 'x-request-id': identifier, 'x-voice-provider': 'qwen',
                       'x-voice-id': 'qwen-voice', 'x-cost-credits': '6'}, wave_bytes()
        with patch('davinci_flow.voice.aurora.request', return_value=result) as network:
            self.assertTrue(recovered.recover().is_file())
        self.assertEqual(network.call_args.args[0], 'GET')
        self.assertIsNone(recovered.pending_id)

    def test_wrong_voice_or_offline_engine_never_sends_a_generation(self):
        self.client.access = normalize_catalog(catalog())
        with patch('davinci_flow.voice.aurora.request') as network:
            with self.assertRaises(AuroraError):
                self.client.generate('Prueba', 'piper-voice', provider='minimax')
            self.client.access['engines'][4]['available'] = False
            with self.assertRaises(AuroraError):
                self.client.generate('Prueba', 'minimax-voice', provider='minimax')
        network.assert_not_called()
        self.assertIsNone(self.client.pending_id)

    def test_internal_access_needs_no_rate_and_unicode_rounding_matches_server(self):
        value = catalog(internal=True)
        value['engines'][4]['rate'] = None
        self.assertTrue(normalize_catalog(value)['engines'][4]['available'])
        self.assertEqual(voice_cost('Prueba', None, internal=True), 0)
        self.assertEqual(voice_cost('🎵' * 201, catalog()['engines'][0]['rate']), 4)
