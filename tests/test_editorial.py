"""Contrato editorial, fuentes offline y fallos de aplicación sin iniciar Resolve."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

from davinci_flow.editorial.model import Decision, EditorialError, Proposal, Snapshot, Template
from davinci_flow.editorial.planner import propose
from davinci_flow.editorial.sources import capture, from_srt, scan_installed
from davinci_flow.editorial.template_files import descriptor, prepare_comp, scan_archive
from davinci_flow.editorial.service import apply_reviewed, undo_reviewed
from davinci_flow.editorial.writer import EditorialWriter, connect_template_output, set_template_text
from davinci_flow.subtitles.model import SubtitleCue


SETTING = '''{ Tools = ordered() {
 MyTitle = MacroOperator {
  Inputs = ordered() { Input1 = InstanceInput { SourceOp = "Text1", Source = "StyledText", }, },
  Outputs = ordered() { Output1 = InstanceOutput { SourceOp = "Text1", Source = "Output", }, },
  Tools = ordered() { Text1 = TextPlus { Inputs = { StyledText = Input { Value = "Original" }, }, }, },
 }, }, }'''


def sample():
    cue = SubtitleCue("No pierdas la ilusión.", 86400, 86448, 1)
    snapshot = Snapshot("Proyecto", "Secuencia", "timeline-1", 24, 1920, 1080, 86400, 1, (cue,), project_id="project-1")
    template = Template("pool_p1", "Texto", "media_pool", "p1")
    decision = Decision(0, "", cue.text, "", {"main": template.id}, "Conservar la frase completa.")
    return Proposal(snapshot, (template,), (decision,), "modelo-seleccionado")


class EditorialContractTests(unittest.TestCase):
    def test_roundtrip_keeps_revision_and_requires_review(self):
        proposal = sample()
        with self.assertRaises(EditorialError):
            proposal.generation_plan()
        proposal = proposal.edit(0, reviewed=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            proposal.save(path)
            loaded = Proposal.load(path)
        self.assertEqual(loaded.revision, proposal.revision)
        self.assertIsNone(loaded.generation_plan().blocks[0].sfx_proposal)

    def test_rejects_lost_negation_and_duplicate_words(self):
        for text in ("Pierdas la ilusión.", "No No pierdas la ilusión."):
            with self.subTest(text=text), self.assertRaises(EditorialError):
                sample().edit(0, main=text)

    def test_manual_edit_requires_note_and_changes_execution_identity(self):
        old = sample().edit(0, reviewed=True)
        new = old.edit(0, main="No pierdas tus sueños.", edit_note="Corrección de Biglex.", reviewed=True)
        self.assertNotEqual(old.generation_plan().plan_id, new.generation_plan().plan_id)

    def test_disabled_blocks_still_require_review(self):
        proposal = sample().edit(0, enabled=False)
        with self.assertRaises(EditorialError):
            proposal.generation_plan()
        self.assertEqual(proposal.edit(0, reviewed=True).generation_plan().active_block_count, 0)

    def test_unknown_template_and_extra_role_are_rejected(self):
        for value in ({"main": "missing"}, {"main": "pool_p1", "accent": "pool_p1"}, {"main": []}):
            with self.subTest(value=value), self.assertRaises(EditorialError):
                sample().edit(0, templates=value)

    def test_nonfinite_and_overlapping_source_times_are_rejected(self):
        s = sample().snapshot
        with self.assertRaises(EditorialError):
            replace(s, fps=float("nan"))
        with self.assertRaises(EditorialError):
            replace(s, cues=s.cues + s.cues)

    def test_llm_cannot_override_review_or_timings(self):
        raw = {"cue_index": 0, "context": "", "main": "No pierdas la ilusión.",
               "accent": "", "templates": {"main": "pool_p1"}, "reason": "Frase completa."}
        for changes in ({"reviewed": True}, {"start_frame": 0}, {"edit_note": "Inventado"}):
            client = Mock(model_name="selected")
            client.generate_json.return_value = {"decisions": [raw | changes]}
            with self.assertRaises(EditorialError):
                propose(sample().snapshot, sample().templates, client)

    def test_llm_uses_context_and_preserves_original(self):
        proposal = sample()
        client = Mock(model_name="selected")
        client.generate_json.return_value = {"decisions": [{
            "cue_index": 0, "context": "No", "main": "pierdas", "accent": "la ilusión.",
            "templates": {"context": "pool_p1", "main": "pool_p1", "accent": "pool_p1"},
            "reason": "Tres jerarquías.",
        }]}
        result = propose(proposal.snapshot, proposal.templates, client)
        self.assertEqual(len(result.decisions[0].templates), 3)
        self.assertFalse(result.decisions[0].reviewed)
        self.assertIn("No pierdas la ilusión.", client.generate_json.call_args.args[0])

    def test_llm_failure_has_no_local_fallback(self):
        client = Mock(model_name="selected")
        client.generate_json.side_effect = TimeoutError("tiempo límite")
        with self.assertRaises(TimeoutError):
            propose(sample().snapshot, sample().templates, client)
        self.assertEqual(client.generate_json.call_count, 1)

    def test_offline_srt_never_connects(self):
        with tempfile.TemporaryDirectory() as tmp, patch("davinci_flow.resolve.connect_to_resolve") as connect:
            path = Path(tmp) / "test.srt"
            path.write_text("1\n00:00:00,000 --> 00:00:02,000\nNo pierdas la ilusión.\n", encoding="utf-8")
            snapshot = from_srt(path, 25)
            self.assertEqual(snapshot.cues[0].end_frame, 50)
            connect.assert_not_called()

    def test_stale_source_stops_before_writer(self):
        proposal = sample().edit(0, reviewed=True)
        changed = replace(proposal.snapshot, width=1080)
        with patch("davinci_flow.editorial.service.capture", return_value=changed), \
             patch("davinci_flow.editorial.service.EditorialWriter") as writer:
            with self.assertRaises(EditorialError):
                apply_reviewed(proposal, Mock(), Path("unused.json"))
            writer.assert_not_called()

    def test_srt_cannot_be_applied_to_unbound_timeline(self):
        proposal = replace(sample().edit(0, reviewed=True), snapshot=replace(sample().snapshot, source="srt"))
        with patch("davinci_flow.editorial.service.capture") as read:
            with self.assertRaises(EditorialError):
                apply_reviewed(proposal, Mock(), Path("unused.json"))
            read.assert_not_called()


class TemplateFileTests(unittest.TestCase):
    def test_group_with_plain_outputs_accepts_main_image_output(self):
        content = SETTING.replace("MacroOperator", "GroupOperator").replace(
            "Outputs = ordered() { Output1", "Outputs = { MainOutput1")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "title.setting"
            path.write_text(content, encoding="utf-8")
            template = scan_installed((root,))[0]
            prepared = prepare_comp(template, root / "prepared").read_text(encoding="utf-8")
            self.assertIn('Source = "MainOutput1"', prepared)

    def test_macro_descriptor_and_output_preserve_internal_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "title.setting"
            path.write_text(SETTING, encoding="utf-8")
            template = scan_installed((root,))[0]
            self.assertEqual(template.text_tool, "MyTitle")
            self.assertEqual(template.text_input, "Input1")
            output = prepare_comp(template, root / "prepared").read_text(encoding="utf-8")
            self.assertIn('SourceOp = "MyTitle", Source = "Output1"', output)
            self.assertIn('Value = "Original"', output)
            self.assertEqual(path.read_text(encoding="utf-8"), SETTING)

    def test_archive_titles_only_and_resources_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "pack.drfx"
            with ZipFile(path, "w") as archive:
                archive.writestr("Edit/Titles/title.setting", SETTING)
                archive.writestr("Edit/Transitions/other.setting", SETTING)
                archive.writestr("Edit/Titles/image.png", b"resource")
            catalog = scan_archive(path)
            self.assertEqual(len(catalog), 1)
            output = prepare_comp(catalog[0], root / "prepared")
            self.assertTrue(output.is_file())
            self.assertEqual((root / "prepared" / catalog[0].id / "Edit/Titles/image.png").read_bytes(), b"resource")

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "pack.drfx"
            with ZipFile(path, "w") as archive:
                archive.writestr("Edit/Titles/title.setting", SETTING)
                archive.writestr("../outside.txt", "invalid")
            with self.assertRaises(EditorialError):
                prepare_comp(scan_archive(path)[0], root / "prepared")
            self.assertFalse((root / "outside.txt").exists())

    def test_corrupt_archive_is_reported_and_other_files_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.drfx").write_text("bad")
            (root / "good.setting").write_text(SETTING)
            diagnostics = []
            self.assertEqual(len(scan_installed((root,), diagnostics)), 1)
            self.assertEqual(len(diagnostics), 1)

    def test_template_changed_after_analysis_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "title.setting"
            path.write_text(SETTING)
            template = scan_installed((Path(tmp),))[0]
            path.write_text(SETTING + " ")
            with self.assertRaises(EditorialError):
                prepare_comp(template, Path(tmp) / "prepared")


class FusionTextTests(unittest.TestCase):
    def test_connects_image_output_instead_of_auxiliary_number_output(self):
        comp, source, target, image_output, number_output, input_ = [Mock() for _ in range(6)]
        comp.FindTool.side_effect = [target, source]
        image_output.GetAttrs.return_value = {"OUTS_DataType": "Image"}
        number_output.GetAttrs.return_value = {"OUTS_DataType": "Number"}
        source.GetOutputList.return_value = {1: number_output, 2: image_output}
        target.GetInputList.return_value = {1: input_}
        input_.GetAttrs.return_value = {"INPS_ID": "Input"}
        input_.GetConnectedOutput.return_value = image_output
        with patch("davinci_flow.editorial.writer.template_bytes", return_value=SETTING.encode()):
            connect_template_output(comp, Mock())
        target.ConnectInput.assert_called_once_with("Input", image_output)

    def test_rejects_import_with_disconnected_media_output(self):
        comp, source, target, output, input_ = [Mock() for _ in range(5)]
        comp.FindTool.side_effect = [target, source]
        source.GetOutputList.return_value = {1: output}
        output.GetAttrs.return_value = {"OUTS_DataType": "Image"}
        target.GetInputList.return_value = {1: input_}
        input_.GetAttrs.return_value = {"INPS_ID": "Input"}
        input_.GetConnectedOutput.return_value = None
        with patch("davinci_flow.editorial.writer.template_bytes", return_value=SETTING.encode()):
            with self.assertRaises(EditorialError):
                connect_template_output(comp, Mock())

    def test_ambiguous_text_nodes_fail(self):
        comp = Mock()
        tools = [Mock(), Mock()]
        for tool in tools:
            tool.GetAttrs.return_value = {"TOOLS_RegID": "TextPlus"}
        comp.GetToolList.return_value = dict(enumerate(tools))
        with self.assertRaises(EditorialError):
            set_template_text(comp, "Texto")
        for tool in tools:
            tool.SetInput.assert_not_called()

    def test_macro_exposed_input_is_verified(self):
        comp = Mock()
        comp.FindTool.return_value.GetInput.return_value = "Texto"
        set_template_text(comp, "Texto", "MyTitle", "Input1")
        comp.FindTool.return_value.SetInput.assert_called_once_with("Input1", "Texto")

    def test_rejected_text_is_not_silently_accepted(self):
        comp = Mock()
        comp.FindTool.return_value.SetInput.return_value = False
        with self.assertRaises(EditorialError):
            set_template_text(comp, "Texto", "MyTitle")


class StrictModelTests(unittest.TestCase):
    def test_404_and_timeout_do_not_switch_model(self):
        from davinci_flow.ai.client import GeminiClient
        from davinci_flow.errors import GeminiError
        import urllib.error
        for error in (TimeoutError(), urllib.error.HTTPError("test", 404, "missing", {}, None)):
            client = GeminiClient(api_key="test-key", model_name="explicit-model", strict_model=True)
            with patch("urllib.request.urlopen", side_effect=error) as request:
                with self.assertRaises(GeminiError):
                    client.generate_json("Prueba")
                self.assertEqual(request.call_count, 1)
                self.assertNotIn("test-key", request.call_args.args[0].full_url)
                self.assertEqual(client.model_name, "explicit-model")


if __name__ == "__main__":
    unittest.main()
