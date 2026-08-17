"""Pruebas unitarias para el escritor de marcadores en DaVinci Resolve."""

import unittest
from unittest.mock import MagicMock

from davinci_flow.ai.aligner import TimelineMarker
from davinci_flow.errors import MarkerError
from davinci_flow.resolve.marker_writer import ResolveMarkerWriter


class MarkerWriterTests(unittest.TestCase):
    """Verifica la inserción y limpieza de marcadores en la línea de tiempo de Resolve."""

    def test_apply_markers_success(self) -> None:
        mock_timeline = MagicMock()
        mock_timeline.GetStartFrame.return_value = 0
        mock_timeline.AddMarker.return_value = True

        markers = [
            TimelineMarker(frame=24.0, color="Cyan", name="Inicio", note="Nota 1"),
            TimelineMarker(frame=100.0, color="Yellow", name="Punto 2", note="Nota 2"),
        ]

        writer = ResolveMarkerWriter(mock_timeline)
        count = writer.apply_markers(markers)

        self.assertEqual(count, 2)
        self.assertEqual(mock_timeline.AddMarker.call_count, 2)
        mock_timeline.AddMarker.assert_any_call(24, "Cyan", "Inicio", "Nota 1", 1)
        mock_timeline.AddMarker.assert_any_call(100, "Yellow", "Punto 2", "Nota 2", 1)

    def test_apply_markers_with_timeline_start_offset(self) -> None:
        mock_timeline = MagicMock()
        mock_timeline.GetStartFrame.return_value = 86400  # 01:00:00:00 a 24fps
        mock_timeline.AddMarker.return_value = True

        markers = [
            TimelineMarker(frame=50.0, color="Pink", name="Énfasis", note="Momento clave"),
        ]

        writer = ResolveMarkerWriter(mock_timeline)
        count = writer.apply_markers(markers)

        self.assertEqual(count, 1)
        mock_timeline.AddMarker.assert_called_once_with(86450, "Pink", "Énfasis", "Momento clave", 1)

    def test_clear_markers_by_color(self) -> None:
        mock_timeline = MagicMock()
        mock_timeline.DeleteMarkersByColor.return_value = True

        writer = ResolveMarkerWriter(mock_timeline)
        result = writer.clear_markers_by_color("Cyan")

        self.assertEqual(result, 1)
        mock_timeline.DeleteMarkersByColor.assert_called_once_with("Cyan")

    def test_unsupported_add_marker_raises_marker_error(self) -> None:
        mock_timeline = object()  # sin método AddMarker
        writer = ResolveMarkerWriter(mock_timeline)
        with self.assertRaises(MarkerError):
            writer.apply_markers([TimelineMarker(frame=10.0)])


if __name__ == "__main__":
    unittest.main()
