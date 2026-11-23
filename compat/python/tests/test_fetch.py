"""Pruebas unitarias para el motor de descarga e importación (Luna Fetch)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from davinci_flow.fetch.engine import FetchEngine
from davinci_flow.fetch.models import (
    FetchProgress,
    FetchRequest,
    FetchResult,
    MediaInfo,
    MediaKind,
)
from davinci_flow.fetch.resolve_importer import ResolveMediaImporter
from davinci_flow.mcp_server import DaVinciFlowMCPServer


class FetchModelsTests(unittest.TestCase):
    """Verifica el formato y comportamiento de los modelos de datos."""

    def test_media_info_duration_display(self) -> None:
        info_zero = MediaInfo(url="http://test", title="Test", duration_seconds=0.0)
        self.assertEqual(info_zero.duration_display, "--:--")

        info_short = MediaInfo(url="http://test", title="Test", duration_seconds=65.0)
        self.assertEqual(info_short.duration_display, "1:05")

        info_long = MediaInfo(url="http://test", title="Test", duration_seconds=3661.0)
        self.assertEqual(info_long.duration_display, "61:01")


class FetchEngineFolderTests(unittest.TestCase):
    """Verifica la resolución de carpetas siguiendo el estándar de Luna Fetch."""

    def test_resolve_destination_creates_separated_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            video_dir = FetchEngine.resolve_destination(base, MediaKind.VIDEO)
            self.assertEqual(video_dir.name, "Videos")
            self.assertTrue(video_dir.is_dir())

            audio_dir = FetchEngine.resolve_destination(base, MediaKind.AUDIO)
            self.assertEqual(audio_dir.name, "Música")
            self.assertTrue(audio_dir.is_dir())

    def test_resolve_destination_does_not_double_nest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "Videos"
            base.mkdir()

            resolved = FetchEngine.resolve_destination(base, MediaKind.VIDEO)
            self.assertEqual(resolved, base)


class ResolveImporterTests(unittest.TestCase):
    """Verifica la organización de carpetas en el Media Pool."""

    def test_resolve_target_folder_hierarchy(self) -> None:
        mock_root = MagicMock()
        mock_root.GetSubFolderList.return_value = []

        mock_media_pool = MagicMock()
        mock_media_pool.GetRootFolder.return_value = mock_root

        def mock_add_sub(parent, name):
            sub = MagicMock()
            sub.GetName.return_value = name
            sub.GetSubFolderList.return_value = []
            return sub

        mock_media_pool.AddSubFolder.side_effect = mock_add_sub

        # Carpeta de video
        video_bin, label_video = ResolveMediaImporter.resolve_target_folder(
            mock_media_pool, MediaKind.VIDEO
        )
        self.assertEqual(label_video, "Luna Fetch/Videos")

        # Carpeta de audio
        audio_bin, label_audio = ResolveMediaImporter.resolve_target_folder(
            mock_media_pool, MediaKind.AUDIO
        )
        self.assertEqual(label_audio, "Luna Fetch/Música")

        # Carpeta personalizada
        custom_bin, label_custom = ResolveMediaImporter.resolve_target_folder(
            mock_media_pool, MediaKind.VIDEO, custom_bin_name="MiCarpeta"
        )
        self.assertEqual(label_custom, "MiCarpeta")


class FetchEngineExecutionTests(unittest.TestCase):
    """Verifica el flujo de descarga simulado de FetchEngine."""

    @patch("davinci_flow.fetch.engine.ResolveMediaImporter.import_to_resolve")
    @patch("yt_dlp.YoutubeDL")
    def test_download_video_and_import(self, mock_ydl_cls, mock_import) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "Videos" / "video_test.mp4"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(b"dummy_mp4_bytes")

            mock_ydl_instance = MagicMock()
            mock_ydl_instance.extract_info.return_value = {
                "title": "Video de prueba",
                "requested_downloads": [{"filepath": str(out_file)}],
            }
            mock_ydl_instance.process_ie_result.return_value = mock_ydl_instance.extract_info.return_value
            mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

            mock_import.return_value = (True, "Luna Fetch/Videos")

            req = FetchRequest(
                url="https://youtube.com/watch?v=123",
                kind=MediaKind.VIDEO,
                output_dir=Path(tmpdir),
                import_to_resolve=True,
            )

            progress_events = []
            result = FetchEngine.download(req, progress_callback=progress_events.append)

            self.assertTrue(result.success)
            self.assertEqual(result.title, "Video de prueba")
            self.assertEqual(result.file_path, out_file)
            self.assertTrue(result.imported_to_resolve)
            self.assertEqual(result.resolve_bin, "Luna Fetch/Videos")
            mock_import.assert_called_once_with(
                file_path=out_file,
                kind=MediaKind.VIDEO,
                custom_bin_name=None,
            )

    @patch('yt_dlp.YoutubeDL')
    def test_unrelated_existing_file_is_never_returned_as_download(self, factory):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / 'Videos' / 'unrelated.mp4'
            old.parent.mkdir()
            old.write_bytes(b'old')
            ydl = factory.return_value.__enter__.return_value
            ydl.extract_info.return_value = {'title': 'Missing result'}
            ydl.process_ie_result.return_value = {'title': 'Missing result'}
            result = FetchEngine.download(FetchRequest('https://example.com/new', output_dir=Path(tmp),
                                                       import_to_resolve=False))
            self.assertFalse(result.success)
            self.assertIsNone(result.file_path)

    @patch('davinci_flow.fetch.engine.ResolveMediaImporter.import_to_resolve')
    @patch('davinci_flow.fetch.engine.shutil.which', return_value='ffmpeg.exe')
    @patch('yt_dlp.YoutubeDL')
    def test_final_postprocessed_file_and_import_error_are_distinct(self, factory, which, importer):
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / 'final.mp3'
            final.write_bytes(b'final audio')
            ydl = factory.return_value.__enter__.return_value
            info = {'title': 'Audio', 'requested_downloads': [{'filepath': str(Path(tmp)/'missing.webm')}]}
            ydl.extract_info.return_value = info
            def process(info, download):
                factory.call_args.args[0]['post_hooks'][0](str(final))
                return info
            ydl.process_ie_result.side_effect = process
            importer.return_value = False, 'Proyecto no disponible'
            result = FetchEngine.download(FetchRequest('https://example.com/audio', MediaKind.AUDIO,
                                                       output_dir=Path(tmp)))
            self.assertTrue(result.success)
            self.assertEqual(result.file_path, final)
            self.assertFalse(result.imported_to_resolve)
            self.assertIsNone(result.resolve_bin)
            self.assertEqual(result.error_message, 'Proyecto no disponible')
            self.assertNotIn('nocheckcertificate', factory.call_args.args[0])

    @patch('yt_dlp.YoutubeDL')
    def test_playlist_is_rejected_before_downloading(self, factory):
        with tempfile.TemporaryDirectory() as tmp:
            ydl = factory.return_value.__enter__.return_value
            ydl.extract_info.return_value = {'_type': 'playlist', 'entries': []}
            result = FetchEngine.download(FetchRequest('https://example.com/playlist', output_dir=Path(tmp)))
            self.assertFalse(result.success)
            ydl.process_ie_result.assert_not_called()

    def test_non_boolean_import_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            FetchRequest('https://example.com/video', import_to_resolve='false')


class MCPFetchToolTests(unittest.TestCase):
    """Verifica la invocación de la herramienta davinciflow_fetch_media en el servidor MCP."""

    @patch("davinci_flow.fetch.engine.FetchEngine.download")
    def test_mcp_fetch_media_tool(self, mock_download) -> None:
        mock_download.return_value = FetchResult(
            success=True,
            url="https://youtube.com/watch?v=xyz",
            title="Video Tutorial",
            file_path=Path("C:/downloads/tutorial.mp4"),
            kind=MediaKind.VIDEO,
            imported_to_resolve=True,
            resolve_bin="Luna Fetch/Videos",
        )

        server = DaVinciFlowMCPServer()
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "davinciflow_fetch_media",
                "arguments": {
                    "url": "https://youtube.com/watch?v=xyz",
                    "kind": "video",
                    "import_to_resolve": True,
                },
            },
        }

        response = server.handle(msg)
        self.assertIsNotNone(response)
        result = response["result"]
        self.assertIn("content", result)
        text_data = result["content"][0]["text"]
        self.assertIn("Video Tutorial", text_data)
        self.assertIn("Luna Fetch/Videos", text_data)


if __name__ == "__main__":
    unittest.main()
