"""Adaptador de solo lectura: una petición JSON por proceso, sin interfaz ni credenciales."""
from contextlib import redirect_stdout
from dataclasses import asdict
import json
import sys

PREFIX = 'DAVINCI_FLOW_GPUI='


def execute(operation):
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
    snapshot, _ = resolve_bridge.read_resolve(track=1, first=1, last=100000)
    return {'project': snapshot.project, 'timeline': snapshot.timeline,
            'fps': snapshot.fps, 'origin': snapshot.origin,
            'cues': [asdict(cue) for cue in snapshot.cues]}


def main():
    try:
        # Las trazas de dependencias no contaminan el protocolo stdout.
        with redirect_stdout(sys.stderr):
            result = execute(sys.argv[1] if len(sys.argv) == 2 else '')
        envelope = {'ok': True, 'result': result}
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    print(PREFIX + json.dumps(envelope, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
