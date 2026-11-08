"""Pruebas unitarias para la integración de títulos nativos de DaVinci Resolve."""

from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.editorial.controller import EditorialController
from davinci_flow.editorial.model import Decision, EditorialOptions, Proposal, Snapshot, Template
from davinci_flow.editorial.writer import EditorialWriter
from davinci_flow.resolve.kinetic_titles import (
    KineticTitleCatalog,
    KineticTitleDescriptor,
    KineticTitleWriter,
)
from davinci_flow.subtitles.model import SubtitleCue


class NativeResolveTitlesTests(unittest.TestCase):
    """Verifica el descubrimiento e inserción nativa de títulos de DaVinci Resolve."""

    def setUp(self) -> None:
        self.catalog = KineticTitleCatalog()

    def test_native_titles_descriptors_available(self) -> None:
        """Comprueba que los títulos nativos clave están presentes en el catálogo."""
        expected_natives = (
            "text_plus",
            "ribbon_text",
            "text_box",
            "fade_on",
            "rise_fade",
            "drop_in",
            "digital_glitch",
            "headline",
            "clean_and_simple",
        )
        for expected_id in expected_natives:
            desc = self.catalog.get(expected_id)
            self.assertEqual(desc.category, "Native")
            self.assertTrue(len(desc.resolve_template_name) > 0)

    def test_native_pack_selection_in_controller(self) -> None:
        """Verifica que el pack 'native' selecciona plantillas nativas de DaVinci."""
        controller = EditorialController()
        # Registrar manualmente plantillas nativas en el catálogo si aún no se han indexado
        for desc in self.catalog.list_by_category("Native")[:10]:
            t = Template(
                id=f"tpl_{desc.id}",
                name=desc.name,
                source="installed_archive",
                locator=f"Templates.drfx::{desc.drfx_rel_path}",
                category="native",
            )
            controller.catalog[t.id] = t

        count = controller.choose_pack("native")
        self.assertGreater(count, 0)
        chosen_ids = {t.id for t in controller.templates}
        self.assertTrue(any("ribbon_text" in tid or "text_box" in tid or "fade_on" in tid for tid in chosen_ids))

    def test_editorial_writer_inserts_native_title_directly(self) -> None:
        """Comprueba que EditorialWriter inserta títulos nativos vía InsertFusionTitleIntoTimeline sin carriers."""
        mock_timeline = MagicMock()
        mock_media_pool = MagicMock()

        mock_timeline.GetTrackCount.return_value = 3
        mock_timeline.GetIsTrackLocked.return_value = False
        mock_timeline.SetTrackLock.return_value = True
        mock_timeline.SetCurrentTimecode.return_value = True
        mock_timeline.SetMarkInOut.return_value = True

        mock_item = MagicMock()
        mock_comp = MagicMock()
        mock_tool = MagicMock()

        mock_item.GetTrackTypeAndIndex.return_value = ("video", 2)
        mock_item.GetStart.return_value = 86400
        mock_item.GetDuration.return_value = 48
        mock_item.GetName.return_value = "DF__item_p1_b1_mai"

        mock_item.GetFusionCompByIndex.return_value = mock_comp
        mock_comp.FindTool.return_value = mock_tool
        mock_timeline.InsertFusionTitleIntoTimeline.return_value = mock_item

        template_native = Template(
            id="tpl_ribbon_text",
            name="Ribbon Text",
            source="installed_archive",
            locator="Templates.drfx::Edit/Titles/Ribbon Text.setting",
            category="native",
        )

        cues = (SubtitleCue("Texto Nativo Ribbon", 86400, 86448, 1),)
        snapshot = Snapshot("Proj", "TL", "tl_1", 24.0, 1920, 1080, 86400, 1, cues)
        decision = Decision(
            cue_index=0,
            context="",
            main="Texto Nativo Ribbon",
            accent="",
            templates={"main": "tpl_ribbon_text"},
            reason="Prueba nativa",
            enabled=True,
            reviewed=True,
        )
        proposal = Proposal(
            snapshot=snapshot,
            templates=(template_native,),
            decisions=(decision,),
            model="test",
            version="1.1.0",
            options=EditorialOptions(track_mode="single"),
        )

        writer = EditorialWriter(
            timeline=mock_timeline,
            media_pool=mock_media_pool,
            proposal=proposal,
            handles={},
        )

        native_name = next(iter(writer.assignments.keys()))
        mock_item.GetName.return_value = native_name

        # Aplicar inserción de la plantilla nativa
        res_item = writer._insert_fusion_title(
            track_index=2,
            start_frame=86400,
            end_frame=86448,
            text="Texto Nativo Ribbon",
            role="main",
            theme=MagicMock(),
            fps=24.0,
            native_name=native_name,
        )

        self.assertIs(res_item, mock_item)
        mock_timeline.InsertFusionTitleIntoTimeline.assert_called_with("Ribbon Text")
        mock_tool.SetInput.assert_any_call("StyledText", "Texto Nativo Ribbon")
        # Asegurar que no se invocó AppendToTimeline (evita carriers)
        mock_media_pool.AppendToTimeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()
