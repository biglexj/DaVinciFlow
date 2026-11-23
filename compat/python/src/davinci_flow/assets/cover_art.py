"""Carátulas de audio: arte embebido en el archivo y carátulas sueltas junto a él.

Solo usa la biblioteca estándar: se leen los contenedores (ID3, FLAC, MP4, Vorbis)
para extraer la imagen sin decodificar audio ni depender de bibliotecas externas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_ART_BYTES = 6 * 1024 * 1024
SIDECAR_NAMES = ("cover", "folder", "front", "album", "albumart", "caratula", "portada", "poster", "thumb")
SIDECAR_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@dataclass(frozen=True)
class CoverArt:
    """Imagen de portada con su procedencia: embebida en el archivo o suelta en la carpeta."""

    data: bytes
    mime: str
    source: str


def image_mime(data: bytes) -> str:
    """Tipo de imagen deducido de los primeros bytes."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"GIF":
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _synchsafe(value: bytes) -> int:
    result = 0
    for byte in value:
        result = (result << 7) | (byte & 0x7F)
    return result


def _plain_size(value: bytes) -> int:
    return int.from_bytes(value, "big")


# --------------------------------------------------------------------------- ID3


def _id3_picture(data: bytes) -> tuple[bytes, str] | None:
    """Extrae la imagen de un bloque ID3v2 (APIC)."""
    if len(data) < 10 or data[:3] != b"ID3":
        return None
    version = data[3]
    size = _synchsafe(data[6:10])
    end = min(len(data), 10 + size)
    offset = 10
    while offset + 10 <= end:
        frame_id = data[offset:offset + 4]
        if frame_id[:1] == b"\x00":
            break
        if version == 2:
            frame_size = int.from_bytes(data[offset + 3:offset + 6], "big")
            header = 6
        else:
            frame_size = _synchsafe(data[offset + 4:offset + 8]) if version == 4 else _plain_size(data[offset + 4:offset + 8])
            header = 10
        body = data[offset + header:offset + header + frame_size]
        offset += header + frame_size
        if frame_id[:4] not in (b"APIC", b"PIC"):
            continue
        picture = _apic_body(body)
        if picture:
            return picture
    return None


def _apic_body(body: bytes) -> tuple[bytes, str] | None:
    if len(body) < 4:
        return None
    encoding = body[0]
    marker = b"\x00\x00" if encoding in (1, 2) else b"\x00"
    mime_end = body.find(marker, 1)
    if mime_end < 0:
        return None
    mime = body[1:mime_end].decode("latin-1", "ignore") or "image/jpeg"
    cursor = mime_end + len(marker)
    if cursor >= len(body):
        return None
    cursor += 1  # tipo de imagen
    if encoding in (1, 2):
        description_end = body.find(b"\x00\x00", cursor)
        cursor = description_end + 2 if description_end >= 0 else len(body)
    else:
        description_end = body.find(b"\x00", cursor)
        cursor = description_end + 1 if description_end >= 0 else len(body)
    payload = body[cursor:]
    if not payload:
        return None
    return payload, mime


def _riff_id3(data: bytes) -> tuple[bytes, str] | None:
    if len(data) < 12 or data[:4] != b"RIFF":
        return None
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset:offset + 4]
        size = _plain_size(data[offset + 4:offset + 8])
        body = data[offset + 8:offset + 8 + size]
        if chunk_id == b"id3 ":
            return _id3_picture(body)
        offset += 8 + size + (size % 2)
    return None


def _aiff_id3(data: bytes) -> tuple[bytes, str] | None:
    if len(data) < 12 or data[:4] not in (b"FORM",):
        return None
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset:offset + 4]
        size = _plain_size(data[offset + 4:offset + 8])
        body = data[offset + 8:offset + 8 + size]
        if chunk_id == b"ID3 ":
            return _id3_picture(body)
        offset += 8 + size + (size % 2)
    return None


# --------------------------------------------------------------------------- FLAC


def _flac_picture_block(block: bytes) -> tuple[bytes, str] | None:
    """Lee un bloque PICTURE de FLAC: tipo, mime, descripción, dimensiones y datos."""
    try:
        cursor = 4
        mime_length = _plain_size(block[cursor:cursor + 4])
        cursor += 4
        mime = block[cursor:cursor + mime_length].decode("latin-1", "ignore")
        cursor += mime_length
        description_length = _plain_size(block[cursor:cursor + 4])
        cursor += 4 + description_length
        cursor += 16  # ancho, alto, profundidad y colores
        data_length = _plain_size(block[cursor:cursor + 4])
        cursor += 4
        payload = block[cursor:cursor + data_length]
    except (IndexError, ValueError):
        return None
    if not payload:
        return None
    return payload, mime or "image/jpeg"


def _flac_picture(data: bytes) -> tuple[bytes, str] | None:
    if len(data) < 8 or data[:4] != b"fLaC":
        return None
    offset = 4
    while offset + 4 <= len(data):
        header = data[offset]
        size = int.from_bytes(data[offset + 1:offset + 4], "big")
        body = data[offset + 4:offset + 4 + size]
        offset += 4 + size
        if header & 0x7F == 6:
            return _flac_picture_block(body)
        if header & 0x80:
            break
    return None


# --------------------------------------------------------------------------- MP4/M4A


def _coverr_payload(body: bytes) -> bytes | None:
    """Extrae la imagen del átomo 'data' que cuelga de 'covr'."""
    offset = 0
    while offset + 8 <= len(body):
        size = int.from_bytes(body[offset:offset + 4], "big")
        atom = body[offset + 4:offset + 8]
        header = 8
        if size == 1 and offset + 16 <= len(body):
            size = int.from_bytes(body[offset + 8:offset + 16], "big")
            header = 16
        elif size == 0:
            size = len(body) - offset
        if size < header:
            break
        payload = body[offset + header:offset + size]
        offset += size
        if atom == b"data" and len(payload) > 8:
            return payload[8:]
    return None


def _mp4_cover(data: bytes) -> tuple[bytes, str] | None:
    """Recorre los átomos MP4 hasta el elemento 'covr' de la lista de metadatos."""
    def walk(chunk: bytes, depth: int = 0) -> tuple[bytes, str] | None:
        offset = 0
        while offset + 8 <= len(chunk) and depth < 8:
            size = int.from_bytes(chunk[offset:offset + 4], "big")
            atom = chunk[offset + 4:offset + 8]
            header = 8
            if size == 1 and offset + 16 <= len(chunk):
                size = int.from_bytes(chunk[offset + 8:offset + 16], "big")
                header = 16
            elif size == 0:
                size = len(chunk) - offset
            if size < header:
                break
            body = chunk[offset + header:offset + size]
            offset += size
            if atom == b"covr":
                payload = _coverr_payload(body)
                return (payload, image_mime(payload)) if payload else None
            if atom in (b"moov", b"udta", b"ilst", b"trak", b"mdia"):
                found = walk(body, depth + 1)
                if found:
                    return found
            elif atom == b"meta":
                found = walk(body[4:], depth + 1)
                if found:
                    return found
        return None

    return walk(data)


# --------------------------------------------------------------------------- OGG


def _ogg_picture(data: bytes) -> tuple[bytes, str] | None:
    """Los OGG guardan la carátula como bloque FLAC codificado en base64."""
    marker = b"METADATA_BLOCK_PICTURE="
    start = data.find(marker)
    if start < 0:
        return None
    end = data.find(b"\x03", start)
    encoded = data[start + len(marker):end if end > 0 else len(data)].strip()
    try:
        import base64
        block = base64.b64decode(encoded, validate=False)
    except (ValueError, TypeError):
        return None
    return _flac_picture_block(block)


def _ogg_comment_picture(packet):
    prefix = 8 if packet.startswith(b'OpusTags') else 7
    if len(packet) < prefix + 4:
        return None
    cursor = prefix + 4 + int.from_bytes(packet[prefix:prefix + 4], 'little')
    count = int.from_bytes(packet[cursor:cursor + 4], 'little')
    cursor += 4
    for _ in range(min(count, 10000)):
        if cursor + 4 > len(packet):
            return None
        size = int.from_bytes(packet[cursor:cursor + 4], 'little')
        cursor += 4
        if cursor + size > len(packet):
            return None
        comment = packet[cursor:cursor + size]
        cursor += size
        if comment.startswith(b'METADATA_BLOCK_PICTURE='):
            return _ogg_picture(comment)
    return None


def _read_ogg_metadata(handle):
    packet = bytearray()
    total = 0
    for _ in range(256):
        header = handle.read(27)
        if len(header) != 27 or header[:4] != b'OggS':
            return None
        lacing = handle.read(header[26])
        if len(lacing) != header[26]:
            return None
        size = sum(lacing)
        total += 27 + len(lacing) + size
        if total > MAX_ART_BYTES:
            return None
        body = handle.read(size)
        if len(body) != size:
            return None
        offset = 0
        for length in lacing:
            packet.extend(body[offset:offset + length])
            offset += length
            if length < 255:
                if packet.startswith((b'\x03vorbis', b'OpusTags')):
                    return _ogg_comment_picture(bytes(packet))
                if not packet.startswith((b'\x01vorbis', b'OpusHead')):
                    return None  # No continuar leyendo paquetes de audio.
                packet.clear()
    return None


# --------------------------------------------------------------------------- API


def embedded_cover(path: str | Path) -> tuple[bytes, str] | None:
    """Devuelve (datos, mime) del arte embebido en el archivo, si lo tiene."""
    file = Path(path)
    suffix = file.suffix.lower()
    if suffix not in ('.mp3', '.aac', '.aiff', '.aif', '.wav', '.m4a', '.mp4', '.flac', '.ogg', '.oga'):
        return None
    try:
        with file.open("rb") as handle:
            return _read_cover_metadata(handle, suffix)
    except OSError:
        return None


def _read_cover_metadata(handle, suffix):
    """Salta los bloques multimedia; solo lee etiquetas y bloques de imagen."""
    header = handle.read(12)
    if header.startswith(b'ID3'):
        size = _synchsafe(header[6:10])
        if size > MAX_ART_BYTES - 10:
            return None
        handle.seek(10)
        return _id3_picture(header[:10] + handle.read(size))
    if suffix == '.flac' and header.startswith(b'fLaC'):
        handle.seek(4)
        for _ in range(1024):
            block = handle.read(4)
            if len(block) != 4:
                break
            size = int.from_bytes(block[1:], 'big')
            if block[0] & 0x7f == 6:
                return _flac_picture_block(handle.read(size)) if size <= MAX_ART_BYTES else None
            handle.seek(size, 1)
            if block[0] & 0x80:
                break
        return None
    if header[:4] in (b'RIFF', b'FORM') and suffix in ('.wav', '.aif', '.aiff'):
        byteorder = 'little' if header[:4] == b'RIFF' else 'big'
        for _ in range(4096):
            chunk = handle.read(8)
            if len(chunk) != 8:
                break
            size = int.from_bytes(chunk[4:], byteorder)
            if chunk[:4].lower() == b'id3 ':
                return _id3_picture(handle.read(size)) if size <= MAX_ART_BYTES else None
            handle.seek(size + size % 2, 1)
        return None
    if suffix in ('.mp4', '.m4a'):
        handle.seek(0, 2)
        end = handle.tell()
        handle.seek(0)
        for _ in range(4096):
            start = handle.tell()
            atom = handle.read(8)
            if len(atom) != 8:
                break
            size, header_size = int.from_bytes(atom[:4], 'big'), 8
            if size == 1:
                extra = handle.read(8)
                if len(extra) != 8:
                    break
                size, header_size = int.from_bytes(extra, 'big'), 16
            elif size == 0:
                size = end - start
            if size < header_size or start + size > end:
                break
            if atom[4:] == b'moov':
                if size > MAX_ART_BYTES:
                    return None
                handle.seek(start)
                return _mp4_cover(handle.read(size))
            handle.seek(start + size)
        return None
    if suffix in ('.ogg', '.oga'):
        handle.seek(0)
        return _read_ogg_metadata(handle)
    return None


def sidecar_image_path(path: str | Path) -> Path | None:
    """Localiza el póster sin cargar sus bytes en Python."""
    file = Path(path)
    folder = file.parent
    candidates = [file.with_suffix(suffix) for suffix in SIDECAR_EXTENSIONS]
    for name in SIDECAR_NAMES:
        candidates.extend(folder / f"{name}{suffix}" for suffix in SIDECAR_EXTENSIONS)
    for candidate in candidates:
        try:
            if not candidate.is_file() or not 0 < candidate.stat().st_size <= MAX_ART_BYTES:
                continue
        except OSError:
            continue
        return candidate
    return None


def sidecar_cover(path: str | Path) -> tuple[bytes, str] | None:
    """Busca una carátula suelta: mismo nombre del archivo o nombres habituales."""
    candidate = sidecar_image_path(path)
    if candidate is not None:
        try:
            payload = candidate.read_bytes()
        except OSError:
            return None
        if payload:
            return payload, image_mime(payload)
    return None


def cover_art(path: str | Path) -> CoverArt | None:
    """Carátula de un archivo de audio: primero la embebida y después la suelta."""
    embedded = embedded_cover(path)
    if embedded:
        return CoverArt(embedded[0], embedded[1], "embedded")
    sidecar = sidecar_cover(path)
    if sidecar:
        return CoverArt(sidecar[0], sidecar[1], "sidecar")
    return None
