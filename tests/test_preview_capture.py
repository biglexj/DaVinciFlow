from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from davinci_flow.editorial.model import EditorialError, Template
from davinci_flow.editorial.preview_capture import capture_in_resolve, ensure_title_thumbnail
from davinci_flow.editorial.title_preview import TitlePreview


class PreviewCaptureTests(unittest.TestCase):
    def test_missing_bin_sample_does_not_contact_resolve(self):
        template = Template('sample', 'Sample', 'installed_bin', 'sample.drb')
        with patch('davinci_flow.editorial.preview_capture.read_title_preview', return_value=TitlePreview()), \
             patch('davinci_flow.editorial.resolve_bridge.request') as request:
            with self.assertRaisesRegex(EditorialError, 'muestra preparada'):
                ensure_title_thumbnail(template)
        request.assert_not_called()

    def test_short_video_retries_from_start_after_failed_seek(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'capture.png'
            template = Template('sample', 'Sample', 'installed_file', 'sample.setting')
            def run(command, **kwargs):
                if command[command.index('-ss') + 1] == '1':
                    return SimpleNamespace(returncode=1)
                Path(command[-1]).write_bytes(b'actual-frame')
                return SimpleNamespace(returncode=0)
            with patch('davinci_flow.editorial.preview_capture.read_title_preview', return_value=TitlePreview(video=Path('short.mp4'))), \
                 patch('davinci_flow.editorial.preview_capture.captured_preview_path', return_value=target), \
                 patch('davinci_flow.editorial.preview_capture.shutil.which', return_value='ffmpeg'), \
                 patch('davinci_flow.editorial.preview_capture.subprocess.run', side_effect=run) as command:
                self.assertEqual(ensure_title_thumbnail(template), target)
            self.assertEqual(target.read_bytes(), b'actual-frame')
            self.assertEqual(command.call_count, 2)
            self.assertEqual(list(Path(tmp).glob('capture-*.png')), [])

    def test_existing_picture_needs_no_ffmpeg_or_resolve(self):
        template = Template('sample', 'Sample', 'installed_file', 'sample.setting')
        with patch('davinci_flow.editorial.preview_capture.read_title_preview', return_value=TitlePreview(image=Path('actual.png'))), \
             patch('davinci_flow.editorial.preview_capture.shutil.which') as ffmpeg:
            self.assertEqual(ensure_title_thumbnail(template), Path('actual.png'))
        ffmpeg.assert_not_called()

    def test_other_project_is_rejected_before_creating_a_timeline(self):
        project = Mock()
        project.GetName.return_value = 'Karaoke - Cumbia Extrangera'
        session = SimpleNamespace(project=project, resolve=Mock())
        template = Template('sample', 'Text+', 'native', 'Text+')
        with self.assertRaisesRegex(EditorialError, 'producción'):
            capture_in_resolve(session, template, Path('capture.png'))
        project.GetMediaPool.assert_not_called()

    def test_failed_export_restores_previous_timeline_head_and_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'capture.png'
            template = Template('sample', 'Text+', 'native', 'Text+')
            p, resolve, manager, pool, previous, temporary, folder = [Mock() for _ in range(7)]
            p.GetName.return_value = 'DF_Validacion_TextPlus_20261109'
            resolve.GetProjectManager.return_value = manager
            manager.GetCurrentDatabase.return_value = {'DbName': 'Contenidos'}
            manager.GetCurrentFolder.return_value = 'Titulos'
            p.GetMediaPool.return_value = pool
            p.GetCurrentTimeline.return_value = previous
            previous.GetCurrentTimecode.return_value = '00:00:42:17'
            pool.GetCurrentFolder.return_value = folder
            pool.CreateEmptyTimeline.return_value = temporary
            p.SetCurrentTimeline.return_value = True
            p.ExportCurrentFrameAsStill.return_value = False
            with patch('davinci_flow.editorial.preview_capture.captured_preview_path', return_value=target), \
                 patch('davinci_flow.editorial.preview_capture.time.sleep'):
                with self.assertRaisesRegex(EditorialError, 'exportar'):
                    capture_in_resolve(SimpleNamespace(project=p, resolve=resolve), template, target)
            self.assertEqual(p.SetCurrentTimeline.call_args.args, (previous,))
            previous.SetCurrentTimecode.assert_called_with('00:00:42:17')
            pool.SetCurrentFolder.assert_called_with(folder)
            pool.DeleteTimelines.assert_called_once_with([temporary])
