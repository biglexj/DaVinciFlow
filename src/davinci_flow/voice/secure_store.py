"""Bóveda Windows por aplicación/checkout, con el mismo contrato DPAPI de Ely."""

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import uuid

from davinci_flow.editorial.model import EditorialError


class SecureStore:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()

    def _crypt(self, data: bytes, decrypt=False) -> bytes:
        if os.name != 'nt':
            raise EditorialError('La bóveda de cuenta todavía requiere Windows.')
        class Blob(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
        def blob(value):
            buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
            return Blob(len(value), buffer)
        source = blob(data)
        entropy = blob(hashlib.sha256(str(self.directory).casefold().encode()).digest())
        output = Blob()
        crypt = ctypes.WinDLL('crypt32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                              ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        operation.restype = wintypes.BOOL
        if not operation(ctypes.byref(source), None, ctypes.byref(entropy), None, None, 1, ctypes.byref(output)):
            raise EditorialError('No se pudo abrir la bóveda de Aurora en este equipo.')
        try:
            return ctypes.string_at(output.data, output.size)
        finally:
            kernel.LocalFree(output.data)

    def read(self, name: str) -> dict | None:
        path = self.directory / (name + '.bin')
        if not path.is_file():
            return None
        try:
            value = json.loads(self._crypt(path.read_bytes(), decrypt=True))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, OSError) as error:
            raise EditorialError('No se pudo leer la sesión guardada de Aurora.') from error

    def write(self, name: str, value: dict):
        encrypted = self._crypt(json.dumps(value).encode())
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / (name + '.bin')
        temporary = target.with_name(uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_bytes(encrypted)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def remove(self, name: str):
        (self.directory / (name + '.bin')).unlink(missing_ok=True)

    def exists(self, name: str) -> bool:
        return (self.directory / (name + '.bin')).is_file()
