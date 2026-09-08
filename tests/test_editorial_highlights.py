"""Contratos de selección, compatibilidad, biblioteca y ventana única."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from davinci_flow.assets.library import scan_library
from davinci_flow.editorial.model import Decision, EditorialError, EditorialOptions, Proposal, digest
from davinci_flow.editorial.planner import propose
from davinci_flow.editorial.preferences import Preferences
from davinci_flow.subtitles.model import SubtitleCue
from test_editorial import sample


def highlights():
    proposal = sample()
    return replace(proposal, version="1.1.0", options=EditorialOptions(),
                   snapshot=replace(proposal.snapshot, cues=(SubtitleCue("Un vídeo para color y otro para transiciones.", 86400, 86448, 1),)),
                   decisions=(replace(proposal.decisions[0], main="COLOR", reason="Concepto dominante."),))


class HighlightTests(unittest.TestCase):
    def test_excerpt_and_no_text_roundtrip(self):
        proposal = highlights().edit(0, reviewed=True)
        self.assertEqual(proposal.generation_plan().blocks[0].main_text, "COLOR")
        empty = proposal.edit(0, main="", enabled=False, templates={}, reason="Dejar respirar la imagen.", reviewed=True)
        self.assertEqual(empty.generation_plan().active_block_count, 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'proposal.json'
            empty.save(path)
            restored = Proposal.load(path)
            self.assertEqual(restored.revision, empty.revision)
            self.assertEqual(restored.options.mode, 'highlights')

    def test_highlight_does_not_invent_or_drop_negation(self):
        with self.assertRaises(EditorialError):
            highlights().edit(0, main="La corrección cinematográfica")
        proposal = replace(sample(), version='1.1.0', options=EditorialOptions())
        with self.assertRaises(EditorialError):
            proposal.edit(0, main="pierdas la ilusión")
        proposal.edit(0, main="No pierdas la ilusión").validate()

    def test_caption_mode_keeps_complete_coverage(self):
        with self.assertRaises(EditorialError):
            replace(highlights(), options=EditorialOptions(mode='captions')).validate()

    def test_legacy_revision_is_unchanged(self):
        proposal = sample()
        data = proposal.to_dict()
        self.assertNotIn('options', data)
        self.assertNotIn('resource_id', data['decisions'][0])
        self.assertEqual(proposal.revision, digest(data))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'legacy.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(Proposal.load(path).revision, digest(data))

    def test_unknown_resource_and_unreviewed_skip_are_rejected(self):
        with self.assertRaises(EditorialError):
            highlights().edit(0, resource_id='inventado')
        empty = highlights().edit(0, main='', templates={}, enabled=False)
        with self.assertRaises(EditorialError):
            empty.generation_plan()

    def test_llm_receives_policy_and_resource_names_only(self):
        client = Mock(model_name='modelo-exacto')
        raw = dict(cue_index=0, context='', main='COLOR', accent='', templates={'main': 'pool_p1'},
                   reason='Destacar el tema.', enabled=True, visual_note='Sobre una imagen de color.', resource_id='visual-1')
        client.generate_json.return_value = {'decisions': [raw]}
        options = EditorialOptions(format='horizontal', direction='Sin karaoke.',
                                   resources=({'id': 'visual-1', 'name': 'color.mov', 'category': 'visuals'},))
        result = propose(highlights().snapshot, highlights().templates, client, options=options)
        self.assertEqual(result.options, options)
        self.assertFalse(result.decisions[0].reviewed)
        prompt = client.generate_json.call_args.args[0]
        self.assertIn('NO subtitules toda la voz', prompt)
        self.assertIn('Sin karaoke.', prompt)
        self.assertIn('color.mov', prompt)
        with self.assertRaises(EditorialError):
            client.generate_json.return_value = {'decisions': [raw | {'reviewed': True}]}
            propose(highlights().snapshot, highlights().templates, client, options=options)


class LibraryTests(unittest.TestCase):
    def test_routes_types_limits_and_missing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('color.mov', 'imagen.png', 'pop.wav', 'guion.md', 'ignore.exe'):
                (root / name).write_bytes(b'')
            resources, diagnostics = scan_library({'visuals': tmp, 'sfx': tmp, 'music': tmp,
                'documents': tmp, 'titles': str(root / 'missing')})
            self.assertEqual(len(resources), 5)
            self.assertEqual(len({r.id for r in resources}), 5)
            self.assertTrue(diagnostics)
            self.assertTrue(all(set(r.context()) == {'id', 'name', 'category'} for r in resources))
            resources, diagnostics = scan_library({'visuals': tmp}, limit=1)
            self.assertEqual(len(resources), 1)
            self.assertIn('limitado', diagnostics[0])

    def test_preferences_preserve_exact_model_and_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'prefs.json'
            prefs = Preferences(model='gemini-3.8-flash', paths={'visuals': tmp, 'music': tmp}, format='horizontal')
            prefs.save(path)
            self.assertEqual(Preferences.load(path), prefs)
            self.assertNotIn('api_key', path.read_text())
            path.write_text('{bad', encoding='utf-8')
            with self.assertRaises(EditorialError):
                Preferences.load(path)


class EntryPointTests(unittest.TestCase):
    def test_native_entry_opens_desktop_without_connecting(self):
        from davinci_flow.ui import open_davinci_flow_ui
        with patch('davinci_flow.ui.desktop_launcher.launch_desktop') as open_ui, \
             patch('davinci_flow.resolve.connect_to_resolve') as connect:
            open_davinci_flow_ui()
            open_ui.assert_called_once_with()
            connect.assert_not_called()

