"""Una ventana por checkout; las siguientes aperturas solicitan traerla al frente."""

import hashlib
import os
from pathlib import Path
import time


class DesktopInstance:
    def __init__(self, directory=None):
        key = hashlib.sha256(str(Path(__file__).resolve()).encode()).hexdigest()[:16]
        self.directory = Path(directory) if directory else Path.home() / '.davinci_flow/runtime' / key
        self.directory.mkdir(parents=True, exist_ok=True)
        self.activation = self.directory / 'activate'
        self.last_activation = self._stamp()
        self.handle = None

    def _stamp(self):
        try:
            return self.activation.read_text(encoding='ascii')
        except FileNotFoundError:
            return ''

    def acquire(self):
        self.handle = (self.directory / 'desktop.lock').open('a+b')
        if self.handle.tell() == 0:
            self.handle.write(b'1')
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            self.activation.write_text(str(time.time_ns()), encoding='ascii')
            return False
        return True

    def activation_requested(self):
        stamp = self._stamp()
        if stamp != self.last_activation:
            self.last_activation = stamp
            return True
        return False

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
