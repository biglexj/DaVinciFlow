"""Pruebas unitarias para GenerationPlan, versionado y serialización."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.errors import PlanSerializationError, PlanVersionMismatchError
from davinci_flow.generation.plan import (
    PLAN_SCHEMA_VERSION,
    GenerationPlan,
    build_generation_plan,
)
from davinci_flow.subtitles.model import SubtitleCue


class GenerationPlanTests(unittest.TestCase):
    """Verifica la construcción, serialización JSON, persistencia y validaciones de GenerationPlan."""

    def setUp(self) -> None:
        self.cues = [
            SubtitleCue(text="Bienvenidos a DaVinci Flow.", start_frame=0.0, end_frame=48.0, track_index=1),
            SubtitleCue(
                text="Por ejemplo, este plan genera capas automáticamente.",
                start_frame=50.0,
                end_frame=120.0,
                track_index=1,
            ),
        ]
        self.plan = build_generation_plan(
            project_name="Proyecto Prueba",
            timeline_name="Timeline 1",
            cues=self.cues,
            track_index=1,
            fps=24.0,
            width=1920,
            height=1080,
            aspect_ratio="16:9",
            theme_name="ely",
            profile_name="natural",
        )

    def test_build_generation_plan_structure(self) -> None:
        self.assertEqual(self.plan.project_name, "Proyecto Prueba")
        self.assertEqual(self.plan.timeline_name, "Timeline 1")
        self.assertEqual(self.plan.block_count, 2)
        self.assertEqual(self.plan.active_block_count, 2)
        self.assertEqual(self.plan.start_frame, 0.0)
        self.assertEqual(self.plan.end_frame, 120.0)
        self.assertEqual(self.plan.schema_version, PLAN_SCHEMA_VERSION)
        self.assertTrue(len(self.plan.source_hash) > 0)

    def test_layer_distribution(self) -> None:
        dist = self.plan.layer_distribution
        self.assertIn(1, dist)
        self.assertIn(2, dist)
        self.assertEqual(dist[1] + dist[2] + dist[3], 2)

    def test_dict_serialization_roundtrip(self) -> None:
        plan_dict = self.plan.to_dict()
        restored = GenerationPlan.from_dict(plan_dict)

        self.assertEqual(restored.plan_id, self.plan.plan_id)
        self.assertEqual(restored.project_name, self.plan.project_name)
        self.assertEqual(restored.source_hash, self.plan.source_hash)
        self.assertEqual(len(restored.blocks), len(self.plan.blocks))
        self.assertEqual(restored.blocks[0].main_text, self.plan.blocks[0].main_text)

    def test_json_serialization_roundtrip(self) -> None:
        json_str = self.plan.to_json()
        restored = GenerationPlan.from_json(json_str)

        self.assertEqual(restored.plan_id, self.plan.plan_id)
        self.assertEqual(restored.blocks[1].normalized_text, self.plan.blocks[1].normalized_text)

    def test_save_and_load_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_plan.json"
            self.plan.save_to_file(file_path)
            self.assertTrue(file_path.is_file())

            loaded_plan = GenerationPlan.load_from_file(file_path)
            self.assertEqual(loaded_plan.plan_id, self.plan.plan_id)
            self.assertEqual(loaded_plan.source_hash, self.plan.source_hash)

    def test_rejects_unsupported_major_version(self) -> None:
        plan_dict = self.plan.to_dict()
        plan_dict["schema_version"] = "99.0.0"
        with self.assertRaises(PlanVersionMismatchError):
            GenerationPlan.from_dict(plan_dict)

    def test_rejects_missing_required_fields_in_deserialization(self) -> None:
        plan_dict = self.plan.to_dict()
        del plan_dict["project_name"]
        with self.assertRaises(PlanSerializationError):
            GenerationPlan.from_dict(plan_dict)

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(PlanSerializationError):
            GenerationPlan.from_json("{invalid_json: 123}")


if __name__ == "__main__":
    unittest.main()
