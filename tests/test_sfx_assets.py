"""Pruebas de los efectos de sonido procedurales incluidos."""

import tempfile
import unittest
import wave

from davinci_flow.sfx.assets import SAMPLE_RATE, ensure_builtin_sfx_assets
from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS


class SfxAssetsTests(unittest.TestCase):
    def test_materializes_valid_mono_wav_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            paths = ensure_builtin_sfx_assets(temp_root)
            self.assertEqual(set(paths), {asset.id for asset in DEFAULT_SFX_ASSETS})

            for descriptor in DEFAULT_SFX_ASSETS:
                path = paths[descriptor.id]
                self.assertTrue(path.is_file())
                with wave.open(str(path), "rb") as wav_file:
                    self.assertEqual(wav_file.getnchannels(), 1)
                    self.assertEqual(wav_file.getframerate(), SAMPLE_RATE)
                    actual_duration = wav_file.getnframes() / SAMPLE_RATE
                    self.assertAlmostEqual(actual_duration, descriptor.duration_seconds, places=3)


if __name__ == "__main__":
    unittest.main()
