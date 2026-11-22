import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from davinci_flow.editorial.model import EditorialError
from davinci_flow.voice.system_tts import SCRIPT, _run, system_voices, synthesize_system
from test_aurora_voice import wave_bytes


class SystemVoiceTests(unittest.TestCase):
    def test_catalog_uses_only_installed_voices_and_keeps_stable_ids(self):
        value = json.dumps([{'id': 'installed', 'name': 'Voz española', 'language': 'es-ES'}, {'name': 'invalid'}])
        with patch('davinci_flow.voice.system_tts.os.name', 'nt'), \
             patch('davinci_flow.voice.system_tts._run', return_value=value):
            first, second = system_voices(), system_voices()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]['system_name'], 'Voz española')
        self.assertEqual(first[0]['provider'], 'system')

    def test_text_is_stdin_json_and_never_interpolated_into_powershell_code(self):
        text = 'DaVinci Flow; $(Write-Output secreto) "ñ"'
        with patch('davinci_flow.voice.system_tts.os.name', 'nt'), \
             patch('davinci_flow.voice.system_tts.subprocess.run', return_value=Mock(returncode=0, stdout='')) as run:
            _run({'action': 'generate', 'text': text})
        self.assertEqual(run.call_args.args[0][-1], SCRIPT)
        self.assertNotIn(text, SCRIPT)
        self.assertEqual(json.loads(run.call_args.kwargs['input'])['text'], text)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_wav_export_is_validated_and_partial_files_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            def create(payload, **kwargs):
                Path(payload['path']).write_bytes(wave_bytes())
            with patch('davinci_flow.voice.system_tts._run', side_effect=create):
                path = synthesize_system('Prueba', {'system_name': 'Instalada'}, folder)
            self.assertEqual(path.read_bytes(), wave_bytes())
            self.assertFalse(list(Path(folder).glob('*.part.wav')))
            def invalid(payload, **kwargs):
                Path(payload['path']).write_bytes(b'invalid')
            with patch('davinci_flow.voice.system_tts._run', side_effect=invalid), self.assertRaises(EditorialError):
                synthesize_system('Prueba', {'system_name': 'Instalada'}, folder)
            self.assertFalse(list(Path(folder).glob('*.part.wav')))
