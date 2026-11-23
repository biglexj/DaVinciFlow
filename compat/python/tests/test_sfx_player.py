import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from davinci_flow.sfx.player import SoundPlayer


class SoundPlayerTests(unittest.TestCase):
    def test_nonexistent_file_returns_false(self):
        player = SoundPlayer()
        self.assertFalse(player.play("non_existent_file_12345.mp3"))
        self.assertIsNone(player.current_path)

    @patch("davinci_flow.sfx.player.os.path.isfile", return_value=True)
    @patch("davinci_flow.sfx.player.sys.platform", "win32")
    def test_play_and_stop_win32_calls_mci(self, mock_isfile):
        player = SoundPlayer(alias="test_alias")
        mock_mci = MagicMock(return_value=0)
        with patch("ctypes.windll.winmm.mciSendStringW", mock_mci, create=True), \
             patch("ctypes.windll.kernel32.GetShortPathNameW", MagicMock(return_value=1), create=True):
            success = player.play("C:/audio/test.mp3")
            self.assertTrue(success)
            self.assertTrue(player.is_playing_path("C:/audio/test.mp3"))

            player.stop()
            self.assertFalse(player.is_playing_path("C:/audio/test.mp3"))
            self.assertIsNone(player.current_path)
