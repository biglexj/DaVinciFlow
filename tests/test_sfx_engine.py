"""Pruebas unitarias para el catálogo y motor de efectos de sonido (SFX) con detección de pausas."""

import unittest

from davinci_flow.sfx.catalog import AssetDescriptor, SFXCatalog, SFXCatalogError
from davinci_flow.sfx.engine import SFXProposalEngine
from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.model import SubtitleCue


class SFXEngineTests(unittest.TestCase):
    """Verifica el cumplimiento de metadatos, licencias, densidad, pausas y exclusiones de SFX."""

    def setUp(self) -> None:
        self.catalog = SFXCatalog()
        self.engine = SFXProposalEngine(self.catalog)

    def test_catalog_has_all_assets_with_license(self) -> None:
        self.assertGreaterEqual(self.catalog.total_assets, 4)
        for asset in self.catalog.list_all():
            self.assertTrue(len(asset.author) > 0)
            self.assertTrue(len(asset.license) > 0)
            self.assertTrue(len(asset.source) > 0)

    def test_rejects_asset_without_license(self) -> None:
        with self.assertRaises(SFXCatalogError):
            AssetDescriptor(
                id="sfx_bad",
                name="Bad Asset",
                category="whoosh",
                relative_path="path/to/bad.wav",
                duration_seconds=1.0,
                author="",  # Vacío
                license="",
                source="",
            )

    def test_assigns_sfx_to_emphasis_block(self) -> None:
        cue = SubtitleCue(text="¡10,000 millones de visitas!", start_frame=0.0, end_frame=48.0, track_index=1)
        block = CaptionBlock(
            id="b1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=48.0,
            original_text=cue.text,
            normalized_text=cue.text,
            main_text="10,000 millones",
            intent="emphasis",
        )
        processed = self.engine.process_blocks([block], profile_name="dinamico")
        self.assertEqual(len(processed), 1)
        self.assertIsNotNone(processed[0].sfx_proposal)

    def test_respects_sfx_off_flag(self) -> None:
        cue = SubtitleCue(text="Momento reflexivo [SFX_OFF]", start_frame=0.0, end_frame=48.0, track_index=1)
        block = CaptionBlock(
            id="b1",
            source_cues=(cue,),
            start_frame=0.0,
            end_frame=48.0,
            original_text=cue.text,
            normalized_text=cue.text,
            main_text="Momento reflexivo",
            intent="emphasis",
        )
        processed = self.engine.process_blocks([block], profile_name="dinamico")
        self.assertIsNone(processed[0].sfx_proposal)

    def test_respects_cooldown_density(self) -> None:
        # Dos bloques con énfasis muy cercanos (menos del cooldown mínimo)
        cue1 = SubtitleCue(text="Primero $100", start_frame=0.0, end_frame=24.0, track_index=1)
        cue2 = SubtitleCue(text="Segundo $200", start_frame=30.0, end_frame=54.0, track_index=1)
        b1 = CaptionBlock(
            id="b1",
            source_cues=(cue1,),
            start_frame=0.0,
            end_frame=24.0,
            original_text=cue1.text,
            normalized_text=cue1.text,
            main_text="Primero $100",
            intent="emphasis",
        )
        b2 = CaptionBlock(
            id="b2",
            source_cues=(cue2,),
            start_frame=30.0,
            end_frame=54.0,
            original_text=cue2.text,
            normalized_text=cue2.text,
            main_text="Segundo $200",
            intent="emphasis",
        )
        processed = self.engine.process_blocks([b1, b2], profile_name="natural")
        # El primero debe tener SFX, el segundo debe omitirlo por cooldown
        self.assertIsNotNone(processed[0].sfx_proposal)
        self.assertIsNone(processed[1].sfx_proposal)

    def test_gap_and_pause_detection_triggers_transition_sfx(self) -> None:
        # Bloque 1 termina en frame 48.0, Bloque 2 inicia en frame 120.0 (gap de 72 frames > 24 frames)
        cue1 = SubtitleCue(text="Primera sección terminada.", start_frame=0.0, end_frame=48.0, track_index=1)
        cue2 = SubtitleCue(text="Siguiente tema importante.", start_frame=150.0, end_frame=198.0, track_index=1)
        b1 = CaptionBlock(
            id="b1",
            source_cues=(cue1,),
            start_frame=0.0,
            end_frame=48.0,
            original_text=cue1.text,
            normalized_text=cue1.text,
            main_text="Primera sección terminada.",
            intent="statement",
        )
        b2 = CaptionBlock(
            id="b2",
            source_cues=(cue2,),
            start_frame=150.0,
            end_frame=198.0,
            original_text=cue2.text,
            normalized_text=cue2.text,
            main_text="Siguiente tema importante.",
            intent="statement",
        )
        processed = self.engine.process_blocks([b1, b2], profile_name="dinamico")
        # El segundo bloque debe recibir un SFX de transición debido a la pausa significativa
        self.assertIsNotNone(processed[1].sfx_proposal)


if __name__ == "__main__":
    unittest.main()
