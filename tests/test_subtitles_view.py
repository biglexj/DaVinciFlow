"""Pruebas unitarias para la pestaña de corrección de subtítulos y el desacople de fases."""

import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import flet as ft

from davinci_flow.editorial.controller import EditorialController
from davinci_flow.editorial.model import Snapshot, SubtitleCue
from app.app import DesktopApp
from features.subtitles.subtitles_view import SubtitlesView


def make_cues():
    return (
        SubtitleCue(text="hola amigos de biglex", start_frame=0.0, end_frame=24.0, track_index=1),
        SubtitleCue(text="hoy veremos davinci studio", start_frame=25.0, end_frame=50.0, track_index=1),
        SubtitleCue(text="que tal como estan todos", start_frame=51.0, end_frame=75.0, track_index=1),
    )


def make_snapshot(cues=None, cuts=((1, 1, 'clip1', 0.0, 100.0, 0.0, 0.0),)):
    return Snapshot(
        project="TestProject",
        timeline="TestTimeline",
        timeline_id="tl_123",
        fps=24.0,
        width=1920,
        height=1080,
        origin=0,
        track=1,
        cues=cues or make_cues(),
        cuts=cuts,
        source="resolve",
        first=1,
        last=10,
        project_id="proj_123",
    )


class SubtitlesViewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.page = Mock()
        self.page.window = Mock()
        self.page.overlay = []
        self.page.update = Mock()
        self.controller = EditorialController()
        self.app = DesktopApp(self.page, self.controller)

    async def test_subtitles_tab_registered_in_app(self):
        self.assertIn('subtitles', self.app.views)
        self.assertIn('subtitles', self.app.labels)
        self.assertEqual(self.app.labels['subtitles'], 'Corrección')
        self.assertIsInstance(self.app.subtitles, SubtitlesView)

    async def test_navigate_to_subtitles_sets_heading(self):
        await self.app.navigate('subtitles')
        self.assertEqual(self.app.current, 'subtitles')
        self.assertEqual(self.app.heading.value, 'Corrección de subtítulos')
        self.assertIs(self.app.workspace.content, self.app.subtitles.content)

    async def test_load_and_refresh_subtitles_from_snapshot(self):
        snapshot = make_snapshot()
        self.controller.snapshot = snapshot
        sub_view = self.app.subtitles
        sub_view.refresh()

        self.assertEqual(len(sub_view.cues), 3)
        self.assertTrue(sub_view.table_view.visible)
        self.assertFalse(sub_view.empty.visible)
        self.assertIn('TestTimeline', sub_view.summary_text.value)
        self.assertIn('3 subtítulos', sub_view.summary_text.value)
        self.assertEqual(len(sub_view.table.rows), 3)

    async def test_find_and_replace(self):
        self.controller.snapshot = make_snapshot()
        sub_view = self.app.subtitles
        sub_view.refresh()

        sub_view.find_field.value = 'biglex'
        sub_view.replace_field.value = 'Biglex J'
        await sub_view.find_and_replace()

        self.assertEqual(sub_view.cues[0].text, 'hola amigos de Biglex J')
        self.assertEqual(sub_view.cues[1].text, 'hoy veremos davinci studio')

    async def test_normalize_all_subtitles(self):
        cues = (
            SubtitleCue(text="  hola   mundo  !  ", start_frame=0.0, end_frame=24.0, track_index=1),
            SubtitleCue(text="que tal ? ", start_frame=25.0, end_frame=50.0, track_index=1),
        )
        self.controller.snapshot = make_snapshot(cues=cues)
        sub_view = self.app.subtitles
        sub_view.refresh()

        await sub_view.normalize_all()

        self.assertEqual(sub_view.cues[0].text, "hola mundo!")
        self.assertEqual(sub_view.cues[1].text, "que tal?")

    async def test_apply_glossary(self):
        self.controller.snapshot = make_snapshot()
        sub_view = self.app.subtitles
        sub_view.refresh()

        sub_view.glossary_field.value = "davinci: DaVinci Resolve, biglex -> Biglex J"
        await sub_view.apply_glossary()

        self.assertEqual(sub_view.cues[0].text, "hola amigos de Biglex J")
        self.assertEqual(sub_view.cues[1].text, "hoy veremos DaVinci Resolve studio")

    async def test_choose_cue_and_edit_manually(self):
        self.controller.snapshot = make_snapshot()
        sub_view = self.app.subtitles
        sub_view.refresh()

        await sub_view.choose_cue(1)
        self.assertTrue(sub_view.editor_card.visible)
        self.assertEqual(sub_view.edit_text_field.value, 'hoy veremos davinci studio')

        sub_view.edit_text_field.value = 'hoy veremos DaVinci Studio 21'
        await sub_view.save_current_cue()

        self.assertEqual(sub_view.cues[1].text, 'hoy veremos DaVinci Studio 21')

    async def test_sync_to_editor(self):
        snapshot = make_snapshot()
        self.controller.snapshot = snapshot
        sub_view = self.app.subtitles
        sub_view.refresh()

        sub_view.find_field.value = 'davinci studio'
        sub_view.replace_field.value = 'DaVinci Resolve Studio 21'
        await sub_view.find_and_replace()

        await sub_view.sync_to_editor()

        self.assertEqual(self.controller.snapshot.cues[1].text, 'hoy veremos DaVinci Resolve Studio 21')

    async def test_subtitles_view_layout_safety(self):
        """Verifica que ningún Row con wrap=True contenga hijos con expand=True (incompatible en Flutter)."""
        sub_view = self.app.subtitles

        def check_control(ctrl):
            if isinstance(ctrl, ft.Row) and getattr(ctrl, 'wrap', False):
                for child in ctrl.controls:
                    self.assertFalse(
                        getattr(child, 'expand', False),
                        f"Control {child} tiene expand=True dentro de un Row con wrap=True, lo cual provoca pantalla gris en Flutter."
                    )
            # Verificar hijos recursivamente
            children = getattr(ctrl, 'controls', None)
            if children:
                for c in children:
                    check_control(c)
            inner = getattr(ctrl, 'content', None)
            if inner:
                check_control(inner)

        check_control(sub_view.content)
        self.assertFalse(getattr(sub_view.script_field, 'expand', False))
        self.assertFalse(getattr(sub_view.edit_text_field, 'expand', False))


class StageDecouplingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.page = Mock()
        self.page.window = Mock()
        self.page.overlay = []
        self.page.update = Mock()
        self.controller = EditorialController()
        self.app = DesktopApp(self.page, self.controller)

    async def test_stage_labels_and_montage_recognition(self):
        editor = self.app.editor
        self.controller.snapshot = make_snapshot()
        editor.refresh()

        self.assertIn("Montaje avanzado", editor.source_summary.value)
        self.assertIn("1 cortes", editor.source_summary.value)

        # Verificar chips
        stage_row = editor.stage_container.content
        assert isinstance(stage_row, ft.Row)
        chips = stage_row.controls
        self.assertEqual(len(chips), 3)
        assert isinstance(chips[0], ft.Container) and isinstance(chips[0].content, ft.Row)
        assert isinstance(chips[1], ft.Container) and isinstance(chips[1].content, ft.Row)
        assert isinstance(chips[2], ft.Container) and isinstance(chips[2].content, ft.Row)
        self.assertEqual(getattr(chips[0].content.controls[1], 'value', None), "1. Montaje y Subtítulos")
        self.assertEqual(getattr(chips[1].content.controls[1], 'value', None), "2. Mesa de Revisión")
        self.assertEqual(getattr(chips[2].content.controls[1], 'value', None), "3. Aplicación en Resolve")

    async def test_interactive_stage_navigation(self):
        editor = self.app.editor
        self.controller.snapshot = make_snapshot()
        editor.refresh()

        # Cambiar interactivamente a la etapa 2 crea propuesta base y no falla
        await editor.set_stage(2)
        self.assertEqual(editor.user_stage, 2)
        self.assertIsNotNone(self.controller.proposal)
        self.assertEqual(len(self.controller.proposal.decisions), 3)

    async def test_direct_review_unlock_on_cue_selection(self):
        editor = self.app.editor
        self.controller.snapshot = make_snapshot()
        self.assertIsNone(self.controller.proposal)
        editor.refresh()

        # Hacer clic en una fila del montaje no bloquea; crea la propuesta directa 1:1
        await editor.choose(0)
        self.assertIsNotNone(self.controller.proposal)
        self.assertTrue(editor.review_card.visible)
        self.assertEqual(editor.texts['main'].value, 'hola amigos de biglex')


class ControllerDirectProposalTests(unittest.TestCase):
    def test_create_default_proposal(self):
        controller = EditorialController()
        controller.snapshot = make_snapshot()
        proposal = controller.create_default_proposal()

        self.assertIsNotNone(proposal)
        self.assertEqual(len(proposal.decisions), 3)
        self.assertEqual(proposal.decisions[0].main, 'hola amigos de biglex')
        self.assertTrue(proposal.decisions[0].enabled)
        self.assertFalse(proposal.decisions[0].reviewed)
        # La propuesta debe validar sin lanzar excepción
        proposal.validate()

    def test_update_cues_syncs_existing_proposal(self):
        controller = EditorialController()
        controller.snapshot = make_snapshot()
        proposal = controller.create_default_proposal()

        updated_cues = (
            SubtitleCue(text="Hola amigos de Biglex J!", start_frame=0.0, end_frame=24.0, track_index=1),
            controller.snapshot.cues[1],
            controller.snapshot.cues[2],
        )
        controller.update_cues(updated_cues)

        self.assertEqual(controller.snapshot.cues[0].text, "Hola amigos de Biglex J!")
        assert controller.proposal is not None
        self.assertEqual(controller.proposal.decisions[0].main, "Hola amigos de Biglex J!")
        controller.proposal.validate()
