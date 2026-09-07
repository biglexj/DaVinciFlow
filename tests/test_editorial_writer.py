"""Recorrido completo simulado: captura, revisión, escritura exacta y reversión."""

from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from davinci_flow.editorial.model import Decision, EditorialError, Proposal
from davinci_flow.editorial.sources import capture, media_pool_catalog
from davinci_flow.editorial.service import apply_reviewed, undo_reviewed


class Tool:
    def __init__(self):
        self.value = "Original"
        self.reject = False

    def GetAttrs(self):
        return {"TOOLS_RegID": "TextPlus"}

    def SetInput(self, key, value):
        if self.reject:
            return False
        self.value = value
        return True

    def GetInput(self, key):
        return self.value


class Comp:
    def __init__(self):
        self.tool = Tool()

    def GetToolList(self, selected):
        return {1: self.tool}

    def SetAttrs(self, attrs):
        self.attrs = attrs
        return True


class Clip:
    def __init__(self, identifier, name, track=1, start=86400, duration=48):
        self.identifier, self.name, self.track = identifier, name, track
        self.start, self.duration = start, duration
        self.comp = Comp()

    def GetUniqueId(self): return self.identifier
    def GetName(self): return self.name
    def SetName(self, value): self.name = value; return True
    def GetStart(self): return self.start
    def GetEnd(self): return self.start + self.duration
    def GetDuration(self): return self.duration
    def GetLeftOffset(self): return 0
    def GetRightOffset(self): return 0
    def GetTrackTypeAndIndex(self): return ["video", self.track]
    def GetFusionCompByIndex(self, index): return self.comp


class Folder:
    def __init__(self, name, clips=(), children=()):
        self.name, self.clips, self.children = name, clips, children

    def GetName(self): return self.name
    def GetClipList(self): return self.clips
    def GetSubFolderList(self): return self.children


class Timeline:
    def __init__(self):
        self.names = ["Vídeo original"]
        self.items = {1: [Clip("source", "Original")]}
        self.cue = Clip("subtitle", "No pierdas la ilusión.")
        self.locked = False

    def GetUniqueId(self): return "timeline-1"
    def GetName(self): return "Secuencia"
    def GetStartFrame(self): return 86400
    def GetSetting(self, key):
        return {"timelineFrameRate": "24", "timelineResolutionWidth": "1920", "timelineResolutionHeight": "1080"}[key]
    def GetTrackCount(self, kind): return len(self.names) if kind == "video" else (1 if kind == "subtitle" else 0)
    def GetTrackName(self, kind, index): return self.names[index - 1]
    def GetItemListInTrack(self, kind, index): return [self.cue] if kind == "subtitle" else self.items.get(index, [])
    def AddTrack(self, kind):
        if kind != "video": raise AssertionError("Fase 1 no crea pistas de audio.")
        self.names.append("")
        return True
    def SetTrackName(self, kind, index, name): self.names[index - 1] = name; return True
    def GetIsTrackLocked(self, kind, index): return self.locked
    def DeleteClips(self, clips, ripple=False):
        for key, values in self.items.items():
            self.items[key] = [v for v in values if v not in clips]
        return True


class Pool:
    def __init__(self, timeline):
        self.timeline = timeline
        self.template = Clip("p1", "Texto propio")
        self.root = Folder("Root", children=[Folder("DaVinci Flow", clips=[self.template])])
        self.count = 0
        self.reject_text = False
        self.wrong_duration = False

    def GetRootFolder(self): return self.root
    def AppendToTimeline(self, infos):
        self.count += 1
        info = infos[0]
        duration = info["endFrame"] - info["startFrame"]
        if self.wrong_duration: duration += 1
        item = Clip(f"created-{self.count}", "Copia", info["trackIndex"], info["recordFrame"], duration)
        item.comp.tool.reject = self.reject_text
        self.timeline.items.setdefault(item.track, []).append(item)
        return [item]


def setup():
    timeline = Timeline()
    pool = Pool(timeline)
    project = SimpleNamespace(GetName=lambda: "Proyecto", GetUniqueId=lambda: "project-1", GetMediaPool=lambda: pool)
    session = SimpleNamespace(timeline=timeline, project=project)
    snapshot = capture(session)
    templates, _ = media_pool_catalog(pool)
    decision = Decision(0, "No", "pierdas", "la ilusión.",
                        {r: templates[0].id for r in ("context", "main", "accent")}, "Tres capas", reviewed=True)
    return session, pool, Proposal(snapshot, templates, (decision,), "test-model")


class EditorialApplicationTests(unittest.TestCase):
    def test_capture_apply_repeat_undo_without_llm_or_original_mutation(self):
        session, pool, proposal = setup()
        with tempfile.TemporaryDirectory() as tmp, patch("davinci_flow.ai.client.GeminiClient") as client:
            record_path = Path(tmp) / "record.json"
            record = apply_reviewed(proposal, session, record_path)
            self.assertEqual(record.item_count, 3)
            self.assertEqual(pool.count, 3)
            self.assertEqual(pool.template.comp.tool.value, "Original")
            self.assertEqual(capture(session).fingerprint, proposal.snapshot.fingerprint)
            apply_reviewed(Proposal.load(record_path.with_suffix(".proposal.json")), session, record_path)
            self.assertEqual(pool.count, 3)
            result = undo_reviewed(session, record_path)
            self.assertEqual(result.status, "reverted")
            self.assertEqual(len(session.timeline.items[1]), 1)
            self.assertEqual(sum(len(v) for k, v in session.timeline.items.items() if k > 1), 0)
            client.assert_not_called()

    def test_text_rejection_rolls_back_inserted_clip(self):
        session, pool, proposal = setup()
        pool.reject_text = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
        self.assertEqual(sum(len(v) for k, v in session.timeline.items.items() if k > 1), 0)

    def test_off_by_one_duration_is_rejected_and_removed(self):
        session, pool, proposal = setup()
        pool.wrong_duration = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
        self.assertEqual(sum(len(v) for k, v in session.timeline.items.items() if k > 1), 0)

    def test_changed_revision_requires_undo_and_preserves_previous_record(self):
        session, pool, proposal = setup()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            apply_reviewed(proposal, session, path)
            before = path.read_bytes()
            changed = proposal.edit(0, enabled=False)
            with self.assertRaises(EditorialError):
                apply_reviewed(changed, session, path)
            self.assertEqual(path.read_bytes(), before)

    def test_manual_text_change_is_preserved_on_reapply(self):
        session, pool, proposal = setup()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            apply_reviewed(proposal, session, path)
            item = session.timeline.items[2][0]
            item.comp.tool.value = "Edición manual"
            with self.assertRaises(Exception):
                apply_reviewed(proposal, session, path)
            self.assertEqual(item.comp.tool.value, "Edición manual")

    def test_cut_change_prevents_any_new_clip(self):
        session, pool, proposal = setup()
        session.timeline.items[1][0].duration = 40
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EditorialError):
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
        self.assertEqual(pool.count, 0)

    def test_locked_track_prevents_new_clip(self):
        session, pool, proposal = setup()
        session.timeline.names += ["DF_CONTEXT", "DF_MAIN", "DF_ACCENT"]
        session.timeline.locked = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EditorialError):
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
        self.assertEqual(pool.count, 0)

    def test_foreign_clip_in_destination_is_not_overwritten(self):
        session, pool, proposal = setup()
        session.timeline.names += ["DF_CONTEXT", "DF_MAIN", "DF_ACCENT"]
        foreign = Clip("foreign", "Título manual", track=3)
        session.timeline.items[3] = [foreign]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EditorialError):
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
        self.assertEqual(pool.count, 0)
        self.assertIn(foreign, session.timeline.items[3])


if __name__ == "__main__":
    unittest.main()
