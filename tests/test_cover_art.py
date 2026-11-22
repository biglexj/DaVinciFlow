"""Lectura de carátulas: arte embebido en el archivo y carátula suelta en la carpeta."""

from pathlib import Path
import tempfile
import unittest
import io
import base64
from unittest.mock import patch

from davinci_flow.assets.cover_art import cover_art, embedded_cover, image_mime, sidecar_cover

JPEG = b"\xff\xd8\xff\xe0" + b"davinci-flow-cover" + b"\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\n" + b"davinci-flow-cover"


def _synchsafe(value: int) -> bytes:
    return bytes(((value >> 21) & 0x7F, (value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F))


def _id3_apic(image: bytes = JPEG, mime: bytes = b"image/jpeg") -> bytes:
    body = b"\x00" + mime + b"\x00" + b"\x03" + b"c\xc3\xa1rtula" + b"\x00" + image
    frame = b"APIC" + len(body).to_bytes(4, "big") + b"\x00\x00" + body
    return b"ID3" + b"\x03\x00" + b"\x00" + _synchsafe(len(frame)) + frame


def _flac_picture(image: bytes = JPEG, mime: bytes = b"image/jpeg") -> bytes:
    block = (b"\x03\x00\x00\x00" + len(mime).to_bytes(4, "big") + mime
             + b"\x00\x00\x00\x00"
             + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
             + len(image).to_bytes(4, "big") + image)
    return b"fLaC" + bytes([6]) + len(block).to_bytes(3, "big") + block


def _mp4_covr(image: bytes = JPEG) -> bytes:
    def atom(name: bytes, payload: bytes) -> bytes:
        return (len(payload) + 8).to_bytes(4, "big") + name + payload

    data = atom(b"data", b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + image)
    covr = atom(b"covr", data)
    ilst = atom(b"ilst", covr)
    meta = atom(b"meta", b"\x00\x00\x00\x00" + ilst)
    udta = atom(b"udta", meta)
    moov = atom(b"moov", udta)
    ftyp = atom(b"ftyp", b"M4A " + b"\x00\x00\x00\x00" + b"M4A mp42isom")
    return ftyp + moov


class CoverArtTests(unittest.TestCase):
    def test_ogg_reads_comment_packet_and_stops_before_audio(self):
        comment = b'METADATA_BLOCK_PICTURE=' + base64.b64encode(_flac_picture()[8:])
        packet = b'OpusTags' + bytes(4) + (1).to_bytes(4, 'little') + len(comment).to_bytes(4, 'little') + comment
        head = b'OpusHead'
        header = b'OggS' + bytes(22) + bytes([2])
        metadata = header + bytes([len(head), len(packet)]) + head + packet
        class Counted(io.BytesIO):
            bytes_read = 0
            def read(self, size=-1):
                value = super().read(size)
                self.bytes_read += len(value)
                return value
        reader = Counted(metadata + bytes(8 * 1024 * 1024))
        with patch.object(Path, 'open', return_value=reader):
            self.assertEqual(embedded_cover('large.ogg')[0], JPEG)
        self.assertLess(reader.bytes_read, 1024)

    def test_no_cover_does_not_read_audio_payload(self):
        class Counted(io.BytesIO):
            bytes_read = 0
            def read(self, size=-1):
                data = super().read(size)
                self.bytes_read += len(data)
                return data
        reader = Counted(b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'\xff' * (8 * 1024 * 1024))
        with patch.object(Path, 'open', return_value=reader):
            self.assertIsNone(embedded_cover('large.mp3'))
        self.assertLess(reader.bytes_read, 32)

    def test_mp4_cover_after_large_media_block_uses_seeking(self):
        fixture = _mp4_covr()
        first_atom = int.from_bytes(fixture[:4], 'big')
        media_size = 8 * 1024 * 1024
        data = fixture[:first_atom] + (media_size + 8).to_bytes(4, 'big') + b'mdat' + bytes(media_size) + fixture[first_atom:]
        class Counted(io.BytesIO):
            bytes_read = 0
            def read(self, size=-1):
                value = super().read(size)
                self.bytes_read += len(value)
                return value
        reader = Counted(data)
        with patch.object(Path, 'open', return_value=reader):
            self.assertEqual(embedded_cover('large.m4a')[0], JPEG)
        self.assertLess(reader.bytes_read, 1024)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_reads_embedded_art_from_id3(self):
        path = self.folder / 'cancion.mp3'
        path.write_bytes(_id3_apic())
        art = cover_art(path)
        self.assertIsNotNone(art)
        self.assertEqual(art.source, 'embedded')
        self.assertEqual(art.data, JPEG)
        self.assertEqual(art.mime, 'image/jpeg')

    def test_reads_embedded_art_from_flac_and_m4a(self):
        flac = self.folder / 'tema.flac'
        flac.write_bytes(_flac_picture())
        m4a = self.folder / 'tema.m4a'
        m4a.write_bytes(_mp4_covr())
        for path in (flac, m4a):
            with self.subTest(path=path.name):
                art = cover_art(path)
                self.assertIsNotNone(art)
                self.assertEqual(art.data, JPEG)

    def test_falls_back_to_sidecar_cover(self):
        path = self.folder / 'tema.mp3'
        path.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00")
        (self.folder / 'tema.jpg').write_bytes(JPEG)
        art = cover_art(path)
        self.assertIsNotNone(art)
        self.assertEqual(art.source, 'sidecar')
        self.assertEqual(art.data, JPEG)

    def test_named_cover_in_folder_is_used(self):
        path = self.folder / 'tema.mp3'
        path.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00")
        (self.folder / 'cover.png').write_bytes(PNG)
        art = cover_art(path)
        self.assertIsNotNone(art)
        self.assertEqual(art.mime, 'image/png')

    def test_without_cover_returns_none(self):
        path = self.folder / 'tema.mp3'
        path.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00")
        self.assertIsNone(cover_art(path))
        self.assertIsNone(embedded_cover(path))
        self.assertIsNone(sidecar_cover(path))

    def test_non_audio_file_is_ignored(self):
        path = self.folder / 'poster.jpg'
        path.write_bytes(JPEG)
        self.assertIsNone(embedded_cover(path))
        self.assertEqual(image_mime(PNG), 'image/png')


if __name__ == '__main__':
    unittest.main()
