from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from davinci_flow.editorial.model import EditorialError
from davinci_flow.fetch.models import MediaKind
from davinci_flow.voice.media import import_voice_file, validate_voice_file, VOICE_BIN


class VoiceMediaTests(unittest.TestCase):
    def test_missing_empty_or_other_file_does_not_contact_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / 'empty.wav'
            empty.touch()
            other = Path(tmp) / 'script.txt'
            other.write_text('narración', encoding='utf-8')
            with patch('davinci_flow.voice.media.ResolveMediaImporter.import_to_resolve') as importer:
                for path in (Path(tmp) / 'missing.wav', empty, other):
                    with self.subTest(path=path), self.assertRaises(EditorialError):
                        import_voice_file(path)
            importer.assert_not_called()

    def test_import_classifies_audio_in_own_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / 'Voice Studio.WAV'
            audio.write_bytes(b'exported-audio')
            with patch('davinci_flow.voice.media.ResolveMediaImporter.import_to_resolve', return_value=(True, VOICE_BIN)) as importer:
                self.assertEqual(import_voice_file(audio), VOICE_BIN)
            importer.assert_called_once_with(audio.resolve(), MediaKind.AUDIO, VOICE_BIN)
            self.assertEqual(validate_voice_file(audio), audio.resolve())

    def test_import_failure_preserves_audio_and_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / 'voice.wav'
            audio.write_bytes(b'exported-audio')
            with patch('davinci_flow.voice.media.ResolveMediaImporter.import_to_resolve', return_value=(False, 'Resolve no responde')) as importer:
                with self.assertRaisesRegex(EditorialError, 'sigue guardado'):
                    import_voice_file(audio)
            importer.assert_called_once()
            self.assertEqual(audio.read_bytes(), b'exported-audio')
