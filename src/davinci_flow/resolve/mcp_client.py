"""Transporte local para el MCP oficial de Blackmagic, sin reintentos implícitos."""

from collections import deque
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from davinci_flow.errors import ResolveConnectionError


class MCPError(ResolveConnectionError):
    """Fallo de protocolo, disponibilidad o ejecución del servidor oficial."""


def find_mcp_executable() -> Path | None:
    configured = os.environ.get('DAVINCIFLOW_RESOLVE_MCP')
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise MCPError('DAVINCIFLOW_RESOLVE_MCP no apunta a un ejecutable existente.')
        return path.resolve()
    if sys.platform == 'win32':
        candidates = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) /
                      'Blackmagic Design/DaVinci Resolve/ResolveMCP.exe']
        # La asociación oficial permite localizar instalaciones en otra unidad.
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'ResolveDrpFile\shell\open\command') as key:
                command = winreg.QueryValue(key, None)
            if command.startswith('"'):
                candidates.append(Path(command.split('"')[1]).parent / 'ResolveMCP.exe')
        except OSError:
            pass
    elif sys.platform == 'darwin':
        candidates = [Path('/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolveMCP')]
    else:
        candidates = [Path('/opt/resolve/bin/ResolveMCP')]
    return next((path for path in candidates if path.is_file()), None)


class ResolveMCP:
    """Una sesión de proceso por operación; llamadas JSON-RPC correlacionadas."""

    def __init__(self, executable: Path, timeout: float = 15):
        self.executable = executable
        self.timeout = timeout
        self.process = None
        self.messages = queue.Queue()
        self.diagnostics = deque(maxlen=16)
        self.threads = []
        self.next_id = 0
        self.server_info = {}

    def __enter__(self):
        try:
            self.process = subprocess.Popen(
                [str(self.executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            for target in (self._read_stdout, self._read_stderr):
                thread = threading.Thread(target=target, daemon=True)
                self.threads.append(thread)
                thread.start()
            initialized = self.rpc('initialize', {
                'protocolVersion': '2024-11-05', 'capabilities': {},
                'clientInfo': {'name': 'davinci-flow', 'version': '1'},
            })
            self.server_info = initialized.get('serverInfo', {})
            if not isinstance(self.server_info, dict) or self.server_info.get('name') != 'davinci_resolve':
                raise MCPError('El ejecutable no respondió como el MCP oficial de Resolve.')
            self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            return self
        except (OSError, MCPError) as error:
            self.close()
            raise MCPError(f'No se pudo conectar con el MCP oficial: {error}') from error

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        for thread in self.threads:
            thread.join(timeout=1)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream:
                stream.close()

    def _read_stdout(self):
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except ValueError:
                    # Diagnósticos nativos no JSON no forman parte del protocolo.
                    self.diagnostics.append(line[:500])
                    continue
                self.messages.put(message)
        finally:
            self.messages.put(None)

    def _read_stderr(self):
        for line in self.process.stderr:
            self.diagnostics.append(line[:500])

    def _send(self, message):
        try:
            self.process.stdin.write(json.dumps(message, ensure_ascii=False, allow_nan=False) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError) as error:
            raise MCPError('Se interrumpió el canal local con Resolve.') from error

    def rpc(self, method, parameters, *, timeout=None):
        self.next_id += 1
        request_id = self.next_id
        self._send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': parameters})
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError('El MCP de Resolve agotó el tiempo de espera.')
            try:
                response = self.messages.get(timeout=remaining)
            except queue.Empty as error:
                raise MCPError('El MCP de Resolve agotó el tiempo de espera.') from error
            if response is None:
                raise MCPError('El MCP de Resolve cerró el canal sin confirmar la operación.')
            if not isinstance(response, dict):
                raise MCPError('Respuesta JSON-RPC de Resolve inválida.')
            if response.get('id') != request_id:
                continue
            if 'error' in response:
                raise MCPError(f"Resolve rechazó la llamada MCP: {response['error']}")
            if response.get('jsonrpc') != '2.0' or not isinstance(response.get('result'), dict):
                raise MCPError('Respuesta JSON-RPC de Resolve inválida.')
            return response['result']

    def call_tool(self, name, arguments=None, *, timeout=None):
        response = self.rpc('tools/call', {'name': name, 'arguments': arguments or {}}, timeout=timeout)
        if response.get('isError'):
            raise MCPError(f'Resolve no pudo ejecutar {name}: {response.get("content", [])}')
        if 'structuredContent' in response:
            data = response['structuredContent']
        else:
            content = response.get('content', [])
            if not isinstance(content, list):
                raise MCPError('La herramienta MCP devolvió contenido inválido.')
            parts = [part.get('text', '') for part in content
                     if isinstance(part, dict) and part.get('type') == 'text']
            try:
                data = json.loads('\n'.join(parts))
            except (ValueError, TypeError) as error:
                raise MCPError('La herramienta MCP no devolvió un resultado JSON válido.') from error
        if not isinstance(data, dict):
            raise MCPError('La herramienta MCP devolvió un resultado inesperado.')
        # Resolve también comunica excepciones dentro del JSON sin isError.
        if 'error' in data:
            raise MCPError(f"Resolve: {data['error']}")
        return data

    def status(self):
        return self.call_tool('get_resolve_status')
