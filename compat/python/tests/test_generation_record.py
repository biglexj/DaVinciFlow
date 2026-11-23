"""Pruebas unitarias para registros de ejecución y auditoría de clips generados."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.generation.record import (
    GenerationExecutionRecord,
    GenerationItemRecord,
)


class GenerationRecordTests(unittest.TestCase):
    """Verifica la persistencia y conteo de ítems aplicados y revertidos."""

    def test_record_item_counts_and_serialization(self) -> None:
        item1 = GenerationItemRecord(
            item_id="item_1",
            block_id="b1",
            role="main",
            track_type="video",
            track_index=3,
            track_name="DF_MAIN",
            start_frame=0.0,
            end_frame=48.0,
            content_text="Texto Principal",
            status="applied",
        )
        item2 = GenerationItemRecord(
            item_id="item_2",
            block_id="b1",
            role="context",
            track_type="video",
            track_index=2,
            track_name="DF_CONTEXT",
            start_frame=0.0,
            end_frame=48.0,
            content_text="Contexto",
            status="applied",
        )
        exec_record = GenerationExecutionRecord(
            execution_id="exec_123",
            plan_id="plan_123",
            source_hash="hash123",
            project_name="Proyecto Test",
            timeline_name="Timeline Test",
            theme_name="ely",
            profile_name="natural",
            items=(item1, item2),
        )

        self.assertEqual(exec_record.item_count, 2)
        self.assertEqual(exec_record.active_item_count, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "exec_record.json"
            exec_record.save_to_file(file_path)
            self.assertTrue(file_path.is_file())

            loaded = GenerationExecutionRecord.load_from_file(file_path)
            self.assertEqual(loaded.execution_id, "exec_123")
            self.assertEqual(len(loaded.items), 2)
            self.assertEqual(loaded.items[0].content_text, "Texto Principal")


if __name__ == "__main__":
    unittest.main()
