"""Contratos del adaptador GPUI, sin red, cobros ni escritura en Resolve."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from dataclasses import replace
from types import SimpleNamespace

BRIDGE = Path(__file__).resolve().parents[1] / 'src-gpui/bridge'


def load(name):
    spec = importlib.util.spec_from_file_location('gpui_' + name, BRIDGE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'protocol': protocol}) if name != 'protocol' else patch.dict(sys.modules, {}):
        spec.loader.exec_module(module)
    return module


protocol = load('protocol')
media = load('media')
editorial = load('editorial')
services = load('services')


class GPUIBridgeTests(unittest.TestCase):
    def test_json_stdin_preserves_multiline_unicode_and_sensitive_arguments(self):
        value = {'operation': 'save_key', 'arguments': {'key': 'test-only-secret', 'text': 'Mañana\n¿sí?'}}
        with patch('sys.stdin', io.StringIO(json.dumps(value))), patch('sys.argv', ['services.py']):
            operation, arguments = protocol.read_request()
        self.assertEqual(operation, 'save_key')
        self.assertEqual(arguments, value['arguments'])

    def test_protocol_rejects_unexpected_fields_and_types(self):
        for value in ([], {'operation': 'apply', 'arguments': [], 'extra': True}, {'operation': 4, 'arguments': {}}):
            with self.subTest(value=value), patch('sys.stdin', io.StringIO(json.dumps(value))):
                with self.assertRaises(ValueError):
                    protocol.read_request()

    def test_unknown_operations_do_not_start_a_service(self):
        for module in (media, editorial, services):
            with self.subTest(module=module.__name__), self.assertRaises(ValueError):
                module.execute('not-allowed', {})

    def test_changed_voice_quote_never_starts_billed_generation(self):
        voice = Mock()
        voice.refresh_access.return_value = {'engines': [{'id': 'gemini', 'available': True, 'rate': {'unit': '200_chars', 'rate_credits': 2, 'is_active': True}}], 'balance': 10}
        with patch.object(media, 'client', return_value=voice):
            with self.assertRaisesRegex(ValueError, 'consumo ha cambiado'):
                media.execute('voice_generate', {'text': 'Hola', 'provider': 'gemini', 'voice': 'test', 'max_cost': 1})
        voice.generate.assert_not_called()

    def test_insufficient_balance_never_starts_billed_generation(self):
        voice = Mock()
        voice.refresh_access.return_value = {'engines': [{'id': 'gemini', 'available': True, 'rate': {'unit': '200_chars', 'rate_credits': 2, 'is_active': True}}], 'balance': 0}
        with patch.object(media, 'client', return_value=voice):
            with self.assertRaisesRegex(ValueError, 'saldo'):
                media.execute('voice_generate', {'text': 'Hola', 'provider': 'gemini', 'voice': 'test', 'max_cost': 2})
        voice.generate.assert_not_called()

    def test_failed_resolve_import_is_an_error(self):
        with patch('davinci_flow.fetch.resolve_importer.ResolveMediaImporter.import_to_resolve', return_value=(False, 'Resolve cerrado')):
            with self.assertRaisesRegex(ValueError, 'Resolve cerrado'):
                media.execute('import_media', {'path': str(Path(__file__).resolve())})

    def test_template_catalog_deduplicates_and_preserves_metadata(self):
        result = services.templates()
        templates = result['templates']
        self.assertTrue(templates)
        self.assertEqual(len(templates), len({item['id'] for item in templates}))
        self.assertTrue(all('text_input' in item and 'fingerprint' in item for item in templates))

    def test_unavailable_aurora_preserves_real_local_voices_and_reports_the_error(self):
        voice = Mock()
        voice.account.restore.side_effect = ValueError('Sin conexión')
        local = [{'id': 'local-test', 'provider': 'system', 'name': 'Voz instalada', 'ready': True}]
        with patch.object(media, 'client', return_value=voice), patch('davinci_flow.voice.system_tts.system_voices', return_value=local):
            result = media.execute('voice_catalog', {})
        self.assertFalse(result['authenticated'])
        self.assertIsNone(result['balance'])
        self.assertEqual(result['voices'], local)
        self.assertIn('Sin conexión', result['warnings'][0])

    def test_ai_uses_corrected_text_without_rewriting_the_resolve_identity(self):
        from davinci_flow.editorial.model import Snapshot, Template, Decision, Proposal, EditorialOptions
        from davinci_flow.subtitles.model import SubtitleCue
        snapshot = Snapshot('Proyecto de prueba', 'Montaje', 'timeline-test', 24, 1920, 1080, 86400, 1,
                            (SubtitleCue('No quiero perder esta idea.', 86424, 86448, 1),), source='resolve')
        decision = Decision(0, '', 'No quiero olvidar esta idea.', '', {'main': 'main'}, 'Revisión', edit_note='Corrección manual')
        proposal = Proposal(snapshot, (Template('main', 'Principal', 'native', 'Text+'),), (decision,), 'manual-direct', '1.1.0', EditorialOptions(mode='captions'))
        received = []

        def generate(corrected, templates, provider, **kwargs):
            received.append(corrected)
            return replace(proposal, snapshot=corrected, decisions=(replace(decision, edit_note=''),))

        with (patch('davinci_flow.editorial.preferences.Preferences.load', return_value=SimpleNamespace(provider='gemini', model='fixture')),
             patch('davinci_flow.ai.providers.factory.build_text_provider', return_value=Mock()),
             patch('davinci_flow.editorial.planner.propose', side_effect=generate)):
            result = editorial.execute('generate', {'proposal': proposal.to_dict()})
        self.assertEqual(received[0].cues[0].text, decision.main)
        self.assertEqual(result['snapshot'], proposal.to_dict()['snapshot'])
        self.assertEqual(result['decisions'][0]['edit_note'], 'Corrección manual')

    def test_markers_require_a_confirmed_resolve_capture(self):
        with patch('davinci_flow.resolve.connect_to_resolve') as connect:
            with self.assertRaisesRegex(ValueError, 'captura identificada'):
                services.execute('insert_markers', {'markers': [{'frame': 1}]})
        connect.assert_not_called()

    def test_marker_insertion_rejects_a_different_timeline_before_writing(self):
        from dataclasses import asdict
        from davinci_flow.editorial.model import Snapshot
        from davinci_flow.subtitles.model import SubtitleCue
        snapshot = Snapshot('Prueba', 'Montaje', 'timeline-test', 24, 1920, 1080, 86400, 1,
                            (SubtitleCue('Prueba', 86424, 86448, 1),), project_id='project-test')
        with (patch('davinci_flow.resolve.connect_to_resolve') as connect,
              patch('davinci_flow.editorial.resolve_bridge.read_resolve', return_value=(replace(snapshot, timeline_id='other'), ()))):
            with self.assertRaisesRegex(ValueError, 'montaje cambió'):
                services.execute('insert_markers', {'snapshot': json.loads(json.dumps(asdict(snapshot))), 'markers': [{'frame': 1}]})
        connect.assert_not_called()

    def test_provider_preview_uses_its_own_model_without_saving_preferences(self):
        from davinci_flow.editorial.preferences import Preferences
        from davinci_flow.ai.providers.base import provider_info
        preferences = Preferences(provider='gemini', model='configured-gemini')
        with (patch('davinci_flow.editorial.preferences.Preferences.load', return_value=preferences),
              patch('davinci_flow.ai.credentials.has_provider_api_key', return_value=False),
              patch.object(Preferences, 'save') as save):
            result = services.execute('settings', {'provider': 'minimax'})
        self.assertEqual(result['provider'], 'minimax')
        self.assertEqual(result['model'], provider_info('minimax').default_model)
        self.assertEqual(preferences.provider, 'gemini')
        save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
