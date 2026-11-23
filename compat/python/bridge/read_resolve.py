"""Adaptador de solo lectura: una petición JSON por proceso, sin interfaz ni credenciales."""
from contextlib import redirect_stdout
from dataclasses import asdict
import json
import sys
from protocol import read_request

PREFIX = 'DAVINCI_FLOW_GPUI='


def parse_arguments(argv):
    """Los argumentos llegan como pares clave=valor; solo se aceptan enteros positivos."""
    values = {}
    for item in argv:
        if '=' not in item:
            raise ValueError('Argumento no válido para el puente de lectura.')
        key, _, raw = item.partition('=')
        try:
            number = int(raw)
        except ValueError:
            raise ValueError(f"El argumento '{key}' debe ser un número entero.") from None
        if number < 0:
            raise ValueError(f"El argumento '{key}' no puede ser negativo.")
        values[key] = number
    return values


def execute(operation, arguments):
    # La lista cerrada evita exponer operaciones de escritura al prototipo.
    if operation not in {'status', 'subtitles'}:
        raise ValueError('Operación de lectura no admitida.')
    from davinci_flow.editorial import resolve_bridge
    if operation == 'status':
        status = resolve_bridge.connection_status()
        # Disponer de Python no demuestra que Resolve esté conectado.
        if status.get('transport') != 'mcp':
            return {'running': False, 'transport': 'legacy',
                    'message': 'La comprobación de disponibilidad requiere el MCP oficial de Resolve.'}
        return {key: status[key] for key in ('running', 'transport', 'version', 'project', 'timeline') if key in status}
    track = arguments.get('track', 1)
    first = arguments.get('first', 1)
    last = arguments.get('last', 100000)
    snapshot, _ = resolve_bridge.read_resolve(track=track, first=first, last=last)
    return asdict(snapshot)


def main():
    try:
        # Las trazas de dependencias no contaminan el protocolo stdout.
        with redirect_stdout(sys.stderr):
            operation, arguments = read_request(parse_arguments)
            arguments = {key: int(value) for key, value in arguments.items()}
            result = execute(operation, arguments)
        envelope = {'ok': True, 'result': result}
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    print(PREFIX + json.dumps(envelope, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
