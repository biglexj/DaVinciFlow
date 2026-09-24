"""Pruebas unitarias para el catálogo e inyector de subtítulos cinéticos nativos."""

from pathlib import Path
import unittest
from unittest.mock import MagicMock

from davinci_flow.resolve.kinetic_titles import (
    BUILTIN_KINETIC_TITLES,
    KineticTitleCatalog,
    KineticTitleDescriptor,
    KineticTitleError,
    KineticTitleWriter,
    frames_to_timecode_string,
    get_default_drfx_path,
)


class TestKineticTitleCatalog(unittest.TestCase):
    """Pruebas de consulta, resolución y extracción de plantillas cinéticas."""

    def setUp(self) -> None:
        self.catalog = KineticTitleCatalog()

    def test_builtin_titles_registered(self) -> None:
        titles = self.catalog.list_all()
        ids = {t.id for t in titles}
        self.assertIn("statement", ids)
        self.assertIn("word_highlight", ids)
        self.assertIn("rotate", ids)
        self.assertIn("lollipop", ids)
        self.assertIn("slide_in", ids)

    def test_get_by_id_case_insensitive(self) -> None:
        desc = self.catalog.get("StAtEmEnT")
        self.assertEqual(desc.id, "statement")
        self.assertEqual(desc.resolve_template_name, "Statement")
        self.assertEqual(desc.category, "Animated")

    def test_get_by_template_name(self) -> None:
        desc = self.catalog.get("Word Highlight")
        self.assertEqual(desc.id, "word_highlight")

    def test_get_unknown_preset_raises_error(self) -> None:
        with self.assertRaises(KineticTitleError):
            self.catalog.get("non_existent_preset_999")

    def test_read_setting_from_drfx_if_file_exists(self) -> None:
        drfx = get_default_drfx_path()
        if drfx and drfx.is_file():
            desc = self.catalog.get("statement")
            content = self.catalog.read_setting_from_drfx(desc)
            self.assertIsNotNone(content)
            self.assertIn("TextPlus", content)
            self.assertIn("StyledText", content)


class TestTimecodeConversion(unittest.TestCase):
    """Pruebas de conversión matemática precisa de fotogramas a código de tiempo."""

    def test_zero_frames(self) -> None:
        self.assertEqual(frames_to_timecode_string(0, 24.0), "00:00:00:00")

    def test_one_second_at_24fps(self) -> None:
        self.assertEqual(frames_to_timecode_string(24, 24.0), "00:00:01:00")

    def test_one_hour_at_24fps(self) -> None:
        self.assertEqual(frames_to_timecode_string(86400, 24.0), "01:00:00:00")

    def test_complex_offset(self) -> None:
        # 86400 + 48 frames = 01:00:02:00
        self.assertEqual(frames_to_timecode_string(86448, 24.0), "01:00:02:00")
        # 86400 + 25 frames = 01:00:01:01
        self.assertEqual(frames_to_timecode_string(86425, 24.0), "01:00:01:01")


class TestKineticTitleWriter(unittest.TestCase):
    """Pruebas de inyección e integración de títulos Fusion en la línea de tiempo."""

    def setUp(self) -> None:
        self.mock_timeline = MagicMock()
        self.mock_media_pool = MagicMock()
        self.writer = KineticTitleWriter(
            timeline=self.mock_timeline,
            media_pool=self.mock_media_pool,
        )

    def test_insert_kinetic_subtitle_via_playhead_and_marks(self) -> None:
        # Configurar mock de timeline
        self.mock_timeline.GetTrackCount.return_value = 3
        self.mock_timeline.GetIsTrackLocked.side_effect = lambda t, idx: False
        self.mock_timeline.SetTrackLock.return_value = True
        self.mock_timeline.SetCurrentTimecode.return_value = True
        self.mock_timeline.SetMarkInOut.return_value = True

        mock_item = MagicMock()
        mock_comp = MagicMock()
        mock_tool = MagicMock()

        mock_item.GetFusionCompByIndex.return_value = mock_comp
        mock_comp.FindTool.return_value = mock_tool

        self.mock_timeline.InsertFusionTitleIntoTimeline.return_value = mock_item

        result = self.writer.insert_kinetic_subtitle(
            track_index=3,
            record_frame=86448,
            duration_frames=48,
            text="¡SUBTÍTULO CINÉTICO!",
            preset_id="statement",
            fps=24.0,
            custom_name="DF_Statement_01",
        )

        self.assertIs(result, mock_item)

        # 1. Comprobar bloqueo temporal de pistas 1 y 2
        self.mock_timeline.SetTrackLock.assert_any_call("video", 1, True)
        self.mock_timeline.SetTrackLock.assert_any_call("video", 2, True)

        # 2. Comprobar posición del cabezal y duración de marcas
        self.mock_timeline.SetCurrentTimecode.assert_called_with("01:00:02:00")
        self.mock_timeline.SetMarkInOut.assert_called_with(86448, 86496)

        # 3. Comprobar inserción con el nombre de plantilla Statement
        self.mock_timeline.InsertFusionTitleIntoTimeline.assert_called_with("Statement")

        # 4. Comprobar restauración de bloqueo y limpieza de marcas
        self.mock_timeline.SetTrackLock.assert_any_call("video", 1, False)
        self.mock_timeline.SetTrackLock.assert_any_call("video", 2, False)
        self.mock_timeline.ClearMarkInOut.assert_called_once()

        # 5. Comprobar asignación de StyledText en el tool
        mock_tool.SetInput.assert_any_call("StyledText", "¡SUBTÍTULO CINÉTICO!")
        mock_item.SetName.assert_called_with("DF_Statement_01")

    def test_insert_fallback_to_media_pool_append(self) -> None:
        # Simular que InsertFusionTitleIntoTimeline no está disponible o falla
        self.mock_timeline.GetTrackCount.return_value = 3
        self.mock_timeline.InsertFusionTitleIntoTimeline.return_value = None

        mock_item = MagicMock()
        mock_comp = MagicMock()
        mock_tool = MagicMock()
        mock_item.GetFusionCompByIndex.return_value = mock_comp
        mock_comp.FindTool.return_value = mock_tool

        # Simular búsqueda de item en el Media Pool
        mock_root = MagicMock()
        mock_pool_item = MagicMock()
        mock_pool_item.GetName.return_value = "Statement"
        mock_root.GetClipList.return_value = [mock_pool_item]
        mock_root.GetSubFolderList.return_value = []
        self.mock_media_pool.GetRootFolder.return_value = mock_root

        self.mock_media_pool.AppendToTimeline.return_value = [mock_item]

        result = self.writer.insert_kinetic_subtitle(
            track_index=3,
            record_frame=100,
            duration_frames=30,
            text="TEXTO APPEND",
            preset_id="statement",
        )

        self.assertIs(result, mock_item)
        self.mock_media_pool.AppendToTimeline.assert_called_once()
        call_args = self.mock_media_pool.AppendToTimeline.call_args[0][0]
        self.assertEqual(len(call_args), 1)
        self.assertEqual(call_args[0]["trackIndex"], 3)
        self.assertEqual(call_args[0]["recordFrame"], 100)
        self.assertEqual(call_args[0]["endFrame"], 30.0)

        mock_tool.SetInput.assert_any_call("StyledText", "TEXTO APPEND")

    def test_update_fusion_text_and_style_variants(self) -> None:
        mock_item = MagicMock()
        mock_comp = MagicMock()
        mock_tool = MagicMock()

        mock_item.GetFusionCompByIndex.return_value = mock_comp
        # Simular que comp encuentra 'Template'
        mock_comp.FindTool.side_effect = lambda name: mock_tool if name == "Template" else None

        success = self.writer.update_fusion_text_and_style(
            item=mock_item,
            text="Texto Actualizado",
            font_name="Montserrat",
            font_style="Black",
            style_overrides={"HBackR": 0.5, "Roundness": 0.2},
        )

        self.assertTrue(success)
        mock_tool.SetInput.assert_any_call("StyledText", "Texto Actualizado")
        mock_tool.SetInput.assert_any_call("Font", "Montserrat")
        mock_tool.SetInput.assert_any_call("Style", "Black")
        mock_tool.SetInput.assert_any_call("HBackR", 0.5)
        mock_tool.SetInput.assert_any_call("Roundness", 0.2)


if __name__ == "__main__":
    unittest.main()
