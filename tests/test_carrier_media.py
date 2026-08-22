import struct
import tempfile
import unittest
from pathlib import Path

from davinci_flow.generation.carrier_media import write_black_uncompressed_avi


class CarrierMediaTests(unittest.TestCase):
    def test_writes_riff_avi_with_requested_frame_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = write_black_uncompressed_avi(
                Path(temp_dir) / "carrier.avi",
                frame_count=48,
                fps=24.0,
            )
            data = output.read_bytes()

        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"AVI ")
        self.assertEqual(struct.unpack("<I", data[4:8])[0], len(data) - 8)
        self.assertEqual(data.count(b"00db"), 96)

    def test_rejects_invalid_media_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "carrier.avi"
            with self.assertRaises(ValueError):
                write_black_uncompressed_avi(path, frame_count=0, fps=24.0)
            with self.assertRaises(ValueError):
                write_black_uncompressed_avi(path, frame_count=1, fps=0.0)


if __name__ == "__main__":
    unittest.main()
