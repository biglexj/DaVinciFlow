"""Recorrido completo simulado: captura, revisión, escritura exacta y reversión."""

from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from davinci_flow.editorial.model import Decision, EditorialConflictError, EditorialError, EditorialOptions, Proposal
from davinci_flow.editorial.sources import capture, media_pool_catalog
from davinci_flow.editorial.service import apply_reviewed, undo_reviewed
from davinci_flow.editorial.writer import EditorialWriter, resolve_user_resource_paths


class Tool:
    def __init__(self):
        self.inputs = {"StyledText": "Original"}
        self.reject = False

    @property
    def value(self):
        return self.inputs.get("StyledText", "Original")

    @value.setter
    def value(self, val):
        self.inputs["StyledText"] = val

    def GetAttrs(self):
        return {"TOOLS_RegID": "TextPlus"}

    def SetInput(self, key, value):
        if self.reject:
            return False
        self.inputs[key] = value
        return True

    def GetInput(self, key):
        return self.inputs.get(key, self.value)


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
            with self.assertRaises(EditorialConflictError) as ctx:
                apply_reviewed(proposal, session, Path(tmp) / "record.json")
            err = ctx.exception
            self.assertTrue(len(err.conflicts) > 0)
            self.assertEqual(err.conflicts[0].clip_name, "Título manual")
            self.assertEqual(err.conflicts[0].track_name, "DF_MAIN")
            self.assertEqual(err.conflicts[0].cue_index, 0)
        self.assertEqual(pool.count, 0)
        self.assertIn(foreign, session.timeline.items[3])

    def test_df_prefixed_clips_are_treated_as_reversion_target_not_foreign_conflict(self):
        session, pool, proposal = setup()
        session.timeline.names += ["DF_CONTEXT", "DF_MAIN", "DF_ACCENT"]
        previous_df_clip = Clip("prev_df", "DF__exec_12345__main_0", track=3)
        session.timeline.items[3] = [previous_df_clip]
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "record.json"
            result = apply_reviewed(proposal, session, record_path)
            self.assertIsNotNone(result)
            self.assertEqual(pool.count, 3)

    def test_resolve_user_resource_paths_and_writer_user_sfx_and_broll_track(self):
        session, pool, base_proposal = setup()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sfx_dir = root / "sfx"
            broll_dir = root / "brolls"
            (sfx_dir / "pops").mkdir(parents=True)
            broll_dir.mkdir(parents=True)
            sfx_file = sfx_dir / "pops" / "custom_pop.wav"
            broll_file = broll_dir / "clip_broll.mp4"
            sfx_file.write_bytes(b"RIFF-test-wav")
            broll_file.write_bytes(b"mp4-test")

            options = EditorialOptions(
                mode="highlights",
                resources=(
                    {"id": "sfx-user-1", "name": "pops/custom_pop.wav", "category": "sfx"},
                    {"id": "broll-user-1", "name": "clip_broll.mp4", "category": "visuals"},
                ),
            )
            decision_sfx = replace(base_proposal.decisions[0], resource_id="sfx-user-1", reviewed=True)
            proposal_sfx = replace(base_proposal, version="1.1.0", options=options, decisions=(decision_sfx,))

            sfx_map, broll_map = resolve_user_resource_paths(
                proposal_sfx, paths={"sfx": str(sfx_dir), "visuals": str(broll_dir)}
            )
            self.assertEqual(sfx_map, {"sfx-user-1": sfx_file.resolve()})
            self.assertEqual(broll_map, {"broll-user-1": broll_file.resolve()})

            # Comprobar que EditorialWriter usa la ruta real de usuario en _insert_sfx
            imported_sfx = Clip("sfx-item-1", "custom_pop.wav", track=1)
            imported_sfx.GetClipProperty = lambda key: "12" if key == "Frames" else ""
            pool.ImportMedia = lambda paths: [imported_sfx]
            pool.AppendToTimeline = lambda infos: [
                SimpleNamespace(
                    GetTrackTypeAndIndex=lambda: ["audio" if infos[0]["mediaType"] == 2 else "video", infos[0]["trackIndex"]],
                    GetStart=lambda: infos[0]["recordFrame"],
                    GetDuration=lambda: infos[0]["endFrame"] - infos[0]["startFrame"],
                    SetName=lambda n: True,
                    GetName=lambda: "DF__exec__sfx",
                )
            ]
            with patch("davinci_flow.editorial.writer.resolve_user_resource_paths", return_value=(sfx_map, broll_map)):
                writer = EditorialWriter(session.timeline, pool, proposal_sfx, {base_proposal.templates[0].id: pool.template})
            audio_item = writer._insert_sfx("sfx-user-1", 1, 86400, 12, "DF__exec__sfx")
            self.assertEqual(audio_item.GetTrackTypeAndIndex(), ["audio", 1])

            # Comprobar que ensure_tracks asegura DF_BROLL si una decisión referencia un B-roll de usuario
            decision_broll = replace(base_proposal.decisions[0], resource_id="broll-user-1", reviewed=True)
            proposal_broll = replace(base_proposal, version="1.1.0", options=options, decisions=(decision_broll,))
            with patch("davinci_flow.editorial.writer.resolve_user_resource_paths", return_value=(sfx_map, broll_map)):
                writer_broll = EditorialWriter(session.timeline, pool, proposal_broll, {base_proposal.templates[0].id: pool.template})
            tracks = writer_broll.ensure_tracks()
            self.assertIn("DF_BROLL", tracks)
            self.assertLess(tracks["DF_BROLL"], tracks["DF_CONTEXT"])

            # Comprobar que apply_reviewed invoca _insert_broll_clip, escribe en DF_BROLL y tolera reaplicación
            broll_pool_clip = Clip("broll-pool-1", "clip_broll.mp4", track=1)
            broll_pool_clip.GetClipProperty = lambda key: "Video" if key == "Type" else ("120" if key == "Frames" else "")

            class ApplyPool(Pool):
                def ImportMedia(self, paths):
                    return [broll_pool_clip]

                def AppendToTimeline(self, infos):
                    self.count += 1
                    info = infos[0]
                    duration = info["endFrame"] - info["startFrame"]
                    item = Clip(f"created-{self.count}", "Copia", info["trackIndex"], info["recordFrame"], duration)
                    self.timeline.items.setdefault(item.track, []).append(item)
                    return [item]

            apply_timeline = Timeline()
            apply_pool = ApplyPool(apply_timeline)
            apply_project = SimpleNamespace(GetName=lambda: "Proyecto", GetUniqueId=lambda: "project-1", GetMediaPool=lambda: apply_pool)
            apply_session = SimpleNamespace(timeline=apply_timeline, project=apply_project)
            snap_broll = capture(apply_session)
            t_broll, _ = media_pool_catalog(apply_pool)
            p_broll = replace(
                proposal_broll,
                snapshot=snap_broll,
                templates=t_broll,
                decisions=(replace(decision_broll, templates={r: t_broll[0].id for r in ("context", "main", "accent")}),),
            )
            record_path = root / "broll_record.json"
            with (
                patch("davinci_flow.editorial.writer.resolve_user_resource_paths", return_value=(sfx_map, broll_map)),
                patch("davinci_flow.editorial.service.capture", return_value=snap_broll),
            ):
                rec = apply_reviewed(p_broll, apply_session, record_path)
                self.assertEqual([item.role for item in rec.items if item.role == "broll"], ["broll"])
                self.assertEqual(next(item.track_name for item in rec.items if item.role == "broll"), "DF_BROLL")
                # Re-aplicar no debe lanzar KeyError en _find_timeline_item
                rec2 = apply_reviewed(Proposal.load(record_path.with_suffix(".proposal.json")), apply_session, record_path)
                self.assertEqual(rec2.item_count, 4)

    def test_scales_25fps_template_source_frames_and_accepts_spanish_captura_still_duration(self):
        session, pool, proposal = setup()
        # Plantilla de 25 fps (32 frames) aplicada en secuencia de 24 fps -> 24f timeline = 25f fuente
        cue_24f = replace(proposal.snapshot.cues[0], start_frame=86400, end_frame=86424)
        snap_24f = replace(proposal.snapshot, fps=24.0, cues=(cue_24f,))
        proposal_24f = replace(proposal, snapshot=snap_24f)

        pool.template.GetClipProperty = lambda key: {
            "Type": "Título – Fusion",
            "FPS": "25.0",
            "Frames": "32",
        }.get(key, "")

        appended_infos = []

        def fake_append(infos):
            appended_infos.append(infos[0])
            tl_dur = round(infos[0]["endFrame"] * 24.0 / 25.0)
            clip = Clip(f"scaled-{len(appended_infos)}", "Copia", infos[0]["trackIndex"], infos[0]["recordFrame"], tl_dur)
            session.timeline.items.setdefault(clip.track, []).append(clip)
            return [clip]

        pool.AppendToTimeline = fake_append
        writer = EditorialWriter(session.timeline, pool, proposal_24f, {proposal.templates[0].id: pool.template})
        item = writer._append_media_item(pool.template, 1, "video", 2, 86400, 24)
        self.assertEqual(appended_infos[0]["endFrame"], 25)
        self.assertEqual(item.GetDuration(), 24)

        # Imagen PNG en español (Type='Captura', Frames='1') cuando Resolve asigna duración fija de 120f
        with tempfile.TemporaryDirectory() as tmp:
            still_path = Path(tmp) / "captura.png"
            still_path.write_bytes(b"PNG")
            still_item = Clip("still-1", "captura.png", track=1)
            still_item.GetClipProperty = lambda key: {"Type": "Captura", "Frames": "1"}.get(key, "")
            pool.ImportMedia = lambda paths: [still_item]

            def append_still(infos):
                clip = Clip("broll-still-1", "Copia", infos[0]["trackIndex"], infos[0]["recordFrame"], 120)
                return [clip]

            pool.AppendToTimeline = append_still
            inserted = writer._insert_broll_clip(str(still_path), 2, 86400, 86424, "DF__exec__broll")
            self.assertEqual(inserted.GetDuration(), 120)


if __name__ == "__main__":
    unittest.main()
