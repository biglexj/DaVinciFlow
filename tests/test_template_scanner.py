"""Pruebas de contratos para escaneo y descubrimiento de presets Text+ en el Media Pool."""

import unittest
from unittest.mock import MagicMock

from davinci_flow.resolve.template_scanner import (
    MediaPoolPreset,
    ensure_davinciflow_bin,
    scan_davinciflow_presets,
)


class TemplateScannerTests(unittest.TestCase):
    def test_excludes_carrier_images_and_video_from_template_bin(self) -> None:
        pool, root, folder = MagicMock(), MagicMock(), MagicMock()
        pool.GetRootFolder.return_value = root
        root.GetSubFolderList.return_value = [folder]
        folder.GetName.return_value = "DaVinciFlow"
        folder.GetSubFolderList.return_value = []
        clips = []
        for name, kind in (("DF_Fusion_Title.png", "Captura"), ("carrier.avi", "Vídeo"),
                           ("biglexpe", "Título – Fusion"), ("Text+", "Fusion Title")):
            clip = MagicMock()
            clip.GetName.return_value = name
            clip.GetClipProperty.return_value = kind
            clips.append(clip)
        folder.GetClipList.return_value = clips
        self.assertEqual([p.name for p in scan_davinciflow_presets(pool)], ["biglexpe", "Text+"])

    def test_scan_davinciflow_presets_finds_clips_and_subfolders(self) -> None:
        mock_media_pool = MagicMock()
        mock_root = MagicMock()
        mock_media_pool.GetRootFolder.return_value = mock_root

        # Folder DaVinciFlow
        df_folder = MagicMock()
        df_folder.GetName.return_value = "DaVinciFlow"

        # Clip inside DaVinciFlow
        clip1 = MagicMock()
        clip1.GetName.return_value = "default_style"
        df_folder.GetClipList.return_value = [clip1]

        # Subfolder biglexj
        subfolder_biglexj = MagicMock()
        subfolder_biglexj.GetName.return_value = "biglexj"
        clip2 = MagicMock()
        clip2.GetName.return_value = "viral_pop"
        subfolder_biglexj.GetClipList.return_value = [clip2]
        subfolder_biglexj.GetSubFolderList.return_value = []

        df_folder.GetSubFolderList.return_value = [subfolder_biglexj]
        mock_root.GetSubFolderList.return_value = [df_folder]

        presets = scan_davinciflow_presets(mock_media_pool)

        self.assertEqual(len(presets), 2)
        self.assertEqual(presets[0].name, "default_style")
        self.assertEqual(presets[0].bin_path, "DaVinciFlow/default_style")
        self.assertEqual(presets[0].display_label, "📁 DaVinciFlow/default_style")

        self.assertEqual(presets[1].name, "viral_pop")
        self.assertEqual(presets[1].bin_path, "DaVinciFlow/biglexj/viral_pop")
        self.assertEqual(presets[1].display_label, "📁 DaVinciFlow/biglexj/viral_pop")

    def test_ensure_davinciflow_bin_creates_when_missing(self) -> None:
        mock_media_pool = MagicMock()
        mock_root = MagicMock()
        mock_root.GetSubFolderList.return_value = []
        mock_media_pool.GetRootFolder.return_value = mock_root

        new_folder = MagicMock()
        mock_media_pool.AddSubFolder.return_value = new_folder

        result = ensure_davinciflow_bin(mock_media_pool)
        self.assertEqual(result, new_folder)
        mock_media_pool.AddSubFolder.assert_called_with(mock_root, "DaVinciFlow")


if __name__ == "__main__":
    unittest.main()
