"""Protocolo local: datos JSON por stdin, nunca credenciales en argv."""
import json
import sys

LIMIT = 32 * 1024 * 1024


def read_request(fallback_parser=None):
    content = sys.stdin.read(LIMIT + 1)
    if len(content.encode('utf-8')) > LIMIT:
        raise ValueError('La petición supera el límite del puente local.')
    if not content.strip():
        operation = sys.argv[1] if len(sys.argv) > 1 else ''
        arguments = fallback_parser(sys.argv[2:]) if fallback_parser else {}
        return operation, arguments
    data = json.loads(content)
    if not isinstance(data, dict) or set(data) != {'operation', 'arguments'}:
        raise ValueError('Petición local inválida.')
    if not isinstance(data['operation'], str) or not isinstance(data['arguments'], dict):
        raise ValueError('Operación o argumentos inválidos.')
    return data['operation'], data['arguments']
