"""Pruebas unitarias para el motor de sincronización de SFX con expresiones visuales."""

from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from davinci_flow.sfx.expression_sync import (
    ExpressionCutEvent,
    SFXExpressionSynchronizer,
)


class TestSFXExpressionSynchronizer(unittest.TestCase):
    """Pruebas de escaneo, detección de cortes, alternancia y colocación de SFX."""

    def setUp(self) -> None:
        self.mock_timeline = MagicMock()
        self.mock_media_pool = MagicMock()
        self.sync_engine = SFXExpressionSynchronizer(
            timeline=self.mock_timeline,
            media_pool=self.mock_media_pool,
            min_cooldown_frames=14,
            swoosh_lead_frames=3,
        )

    def _create_mock_clip(self, start_frame: int, name: str) -> MagicMock:
        clip = MagicMock()
        clip.GetStart.return_value = start_frame
        clip.GetName.return_value = name
        return clip

    def test_scan_expression_cuts_with_alternation_and_cooldown(self) -> None:
        # Pista V4 con varios clips de expresiones de personaje
        clips = [
            self._create_mock_clip(0, "Expresiones_Alegre.webp"),
            self._create_mock_clip(48, "Expresiones_Sorpresa.webp"),
            self._create_mock_clip(120, "Ely_Movimiento_Swoosh.webp"),
            # Clip muy cercano al anterior (125 - 117 = 8 fotogramas < 14 cooldown)
            self._create_mock_clip(125, "Expresiones_Curiosa.webp"),
            self._create_mock_clip(180, "Expresiones_Pensativa.webp"),
        ]

        self.mock_timeline.GetItemListInTrack.return_value = clips

        events = self.sync_engine.scan_expression_cuts(expression_track_index=4)

        # Deberían registrarse 4 eventos (el de frame 125 se omite por cooldown)
        self.assertEqual(len(events), 4)

        # Evento 0: primer corte estándar -> pop_02
        self.assertEqual(events[0].frame, 0)
        self.assertEqual(events[0].target_frame, 0)
        self.assertEqual(events[0].event_type, "pop")
        self.assertEqual(events[0].sfx_asset_name, "pop_02")
        self.assertEqual(events[0].lead_frames, 0)

        # Evento 1: segundo corte -> alternado a suction_pop_07
        self.assertEqual(events[1].frame, 48)
        self.assertEqual(events[1].target_frame, 48)
        self.assertEqual(events[1].event_type, "pop")
        self.assertEqual(events[1].sfx_asset_name, "suction_pop_07")

        # Evento 2: corte de movimiento/swoosh -> anticipación de 3 fotogramas
        self.assertEqual(events[2].frame, 120)
        self.assertEqual(events[2].target_frame, 117)  # 120 - 3
        self.assertEqual(events[2].event_type, "swoosh")
        self.assertEqual(events[2].sfx_asset_name, "swoosh_02")
        self.assertEqual(events[2].lead_frames, 3)

        # Evento 3: tras el salto (frame 180) -> pop alternado
        self.assertEqual(events[3].frame, 180)
        self.assertEqual(events[3].target_frame, 180)
        self.assertEqual(events[3].event_type, "pop")
        self.assertEqual(events[3].sfx_asset_name, "pop_02")

    def test_apply_sfx_sync_dry_run_does_not_modify_timeline(self) -> None:
        clips = [self._create_mock_clip(0, "Expresiones_Alegre.webp")]
        self.mock_timeline.GetItemListInTrack.return_value = clips

        events = self.sync_engine.apply_sfx_sync(
            expression_track_index=4,
            sfx_audio_track_index=4,
            dry_run=True,
        )

        self.assertEqual(len(events), 1)
        self.mock_media_pool.AppendToTimeline.assert_not_called()

    def test_apply_sfx_sync_appends_audio_clips(self) -> None:
        clips = [
            self._create_mock_clip(0, "Expresiones_Alegre.webp"),
            self._create_mock_clip(60, "Expresiones_Sorpresa.webp"),
        ]
        self.mock_timeline.GetItemListInTrack.return_value = clips
        self.mock_timeline.GetTrackCount.return_value = 4

        mock_media_item = MagicMock()
        mock_media_item.GetName.return_value = "pop_02.mp3"
        mock_timeline_item = MagicMock()

        self.mock_media_pool.AppendToTimeline.return_value = [mock_timeline_item]

        # Inyectar el media item en la caché para evitar acceso a disco en la prueba unitaria
        self.sync_engine._imported_sfx_cache["pop_02"] = mock_media_item
        self.sync_engine._imported_sfx_cache["suction_pop_07"] = mock_media_item

        applied = self.sync_engine.apply_sfx_sync(
            expression_track_index=4,
            sfx_audio_track_index=4,
            dry_run=False,
        )

        self.assertEqual(len(applied), 2)
        self.assertEqual(self.mock_media_pool.AppendToTimeline.call_count, 2)

        # Comprobar el primer AppendToTimeline
        first_call = self.mock_media_pool.AppendToTimeline.call_args_list[0][0][0]
        self.assertEqual(first_call[0]["trackIndex"], 4)
        self.assertEqual(first_call[0]["mediaType"], 2)  # Audio
        self.assertEqual(first_call[0]["recordFrame"], 0)

        # Comprobar el segundo AppendToTimeline
        second_call = self.mock_media_pool.AppendToTimeline.call_args_list[1][0][0]
        self.assertEqual(second_call[0]["trackIndex"], 4)
        self.assertEqual(second_call[0]["mediaType"], 2)  # Audio
        self.assertEqual(second_call[0]["recordFrame"], 60)


if __name__ == "__main__":
    unittest.main()
