"""Generación de un vídeo portador mínimo para clips Fusion de duración exacta."""

from __future__ import annotations

import struct
from fractions import Fraction
from pathlib import Path


def _chunk(fourcc: bytes, payload: bytes) -> bytes:
    padding = b"\x00" if len(payload) % 2 else b""
    return fourcc + struct.pack("<I", len(payload)) + payload + padding


def _list_chunk(list_type: bytes, payload: bytes) -> bytes:
    return _chunk(b"LIST", list_type + payload)


def write_black_uncompressed_avi(
    path: str | Path,
    frame_count: int,
    fps: float,
    width: int = 4,
    height: int = 4,
) -> Path:
    """Escribe un AVI BI_RGB diminuto y válido usando únicamente la biblioteca estándar."""
    if frame_count < 1:
        raise ValueError("El AVI portador necesita al menos un fotograma.")
    if fps <= 0:
        raise ValueError("Los FPS del AVI portador deben ser positivos.")
    if width < 1 or height < 1:
        raise ValueError("Las dimensiones del AVI portador deben ser positivas.")

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame_rate = Fraction(str(fps)).limit_denominator(1001)
    rate, scale = frame_rate.numerator, frame_rate.denominator
    row_stride = ((width * 3 + 3) // 4) * 4
    frame_size = row_stride * height
    frame_data = b"\x00" * frame_size

    microseconds_per_frame = int(round(1_000_000 * scale / rate))
    max_bytes_per_second = int(round(frame_size * rate / scale))
    avih = struct.pack(
        "<IIIIIIIIII4I",
        microseconds_per_frame,
        max_bytes_per_second,
        0,
        0x10,
        frame_count,
        0,
        1,
        frame_size,
        width,
        height,
        0,
        0,
        0,
        0,
    )
    stream_header = struct.pack(
        "<4s4sIHHIIIIIIIIhhhh",
        b"vids",
        b"DIB ",
        0,
        0,
        0,
        0,
        scale,
        rate,
        0,
        frame_count,
        frame_size,
        0xFFFFFFFF,
        0,
        0,
        0,
        width,
        height,
    )
    bitmap_info = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        24,
        0,
        frame_size,
        0,
        0,
        0,
        0,
    )
    stream_list = _list_chunk(
        b"strl",
        _chunk(b"strh", stream_header) + _chunk(b"strf", bitmap_info),
    )
    header_list = _list_chunk(b"hdrl", _chunk(b"avih", avih) + stream_list)

    movie_payload = bytearray()
    index_entries = bytearray()
    offset = 4
    for _ in range(frame_count):
        frame_chunk = _chunk(b"00db", frame_data)
        movie_payload.extend(frame_chunk)
        index_entries.extend(struct.pack("<4sIII", b"00db", 0x10, offset, frame_size))
        offset += len(frame_chunk)

    movie_list = _list_chunk(b"movi", bytes(movie_payload))
    index_chunk = _chunk(b"idx1", bytes(index_entries))
    avi_payload = b"AVI " + header_list + movie_list + index_chunk
    output.write_bytes(b"RIFF" + struct.pack("<I", len(avi_payload)) + avi_payload)
    return output
