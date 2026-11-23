"""Pruebas unitarias para el catálogo de B-Rolls y escáner de assets del usuario."""

import tempfile
import unittest
from pathlib import Path

from davinci_flow.assets.broll_catalog import (
    AssetCollection,
    BRollAsset,
    _extract_tags_from_path,
    scan_assets_directory,
)


class BRollCatalogTests(unittest.TestCase):
    def test_extract_tags_cleans_and_filters_stop_words(self) -> None:
        p = Path("C:/Assets/Tech_Videos/broll_programacion_codigo_ia.mp4")
        tags = _extract_tags_from_path(p)
        self.assertIn("programacion", tags)
        self.assertIn("codigo", tags)
        self.assertIn("ia", tags)
        self.assertNotIn("broll", tags)

    def test_broll_asset_matching_query_score(self) -> None:
        asset = BRollAsset(
            id="asset_01",
            name="grafico_finanzas_dinero.mp4",
            file_path="/path/grafico.mp4",
            asset_type="video",
            tags=("grafico", "finanzas", "dinero", "inversion"),
        )
        score_exact = asset.matches_query(["dinero", "finanzas"])
        self.assertGreaterEqual(score_exact, 4.0)

        score_partial = asset.matches_query(["inver"])
        self.assertGreaterEqual(score_partial, 1.0)

        score_none = asset.matches_query(["cocina", "receta"])
        self.assertEqual(score_none, 0.0)

    def test_scan_assets_directory_indexes_videos_and_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "brolls").mkdir()
            (root / "sfx").mkdir()

            (root / "brolls" / "codigo_python.mp4").write_bytes(b"dummy")
            (root / "brolls" / "interfaz_davinci.mov").write_bytes(b"dummy")
            (root / "sfx" / "whoosh_rapido.wav").write_bytes(b"dummy")
            (root / "readme.txt").write_text("ignorar", encoding="utf-8")

            collection = scan_assets_directory(root)
            self.assertEqual(collection.total_count, 3)
            self.assertEqual(len(collection.video_assets), 2)
            self.assertEqual(len(collection.audio_assets), 1)

            best, score = collection.find_best_match(["python", "codigo"], asset_type="video")
            self.assertIsNotNone(best)
            assert best is not None
            self.assertEqual(best.name, "codigo_python.mp4")


if __name__ == "__main__":
    unittest.main()
