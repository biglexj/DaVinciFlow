"""Ejecuta las operaciones editoriales cerradas en el Python integrado de Resolve."""

import json
from pathlib import Path

from davinci_flow.editorial.model import EditorialError, Proposal
from davinci_flow.resolve.mcp_client import MCPError, ResolveMCP


def request(executable, operation, parameters):
    # No se envían propuestas pendientes de revisión al proceso de Resolve.
    if operation == 'apply':
        Proposal.load(parameters['proposal_path']).validate(require_review=True)
    source = str(Path(__file__).resolve().parents[2])
    payload = json.dumps({'operation': operation, 'parameters': parameters}, ensure_ascii=False, allow_nan=False)
    # El modo con acceso al sistema es necesario para importar nuestro paquete
    # y acceder a propuestas, archivos Fusion y registros de reversión locales.
    # Solo se transmite código fijo; los parámetros son datos JSON, nunca código.
    script = '\n'.join([
        'import sys, json',
        '_flow_path = sys.path[:]',
        'try:',
        f'    sys.path.insert(0, {source!r})',
        '    from davinci_flow.editorial.resolve_bridge import dispatch',
        '    from davinci_flow.resolve.client import connect_to_resolve',
        f'    _flow_payload = json.loads({payload!r})',
        '    _flow_session = connect_to_resolve(resolve)',
        "    result = {'ok': True, 'result': dispatch(_flow_payload['operation'],",
        "              _flow_payload['parameters'], session=_flow_session)}",
        'except Exception as error:',
        "    result = {'ok': False, 'error': str(error)}",
        'finally:',
        '    sys.path[:] = _flow_path',
    ])
    writing = operation in {'apply', 'undo'}
    dispatched = False
    try:
        with ResolveMCP(executable) as client:
            if client.status().get('running') is not True:
                raise EditorialError('Resolve Studio no está disponible. Abre el proyecto y la secuencia.')
            dispatched = True
            data = client.call_tool('run_script_unsafe', {'script': script, 'timeout': 60}, timeout=75)
            envelope = data.get('result')
            if not isinstance(envelope, dict) or type(envelope.get('ok')) is not bool:
                raise MCPError('Resolve no confirmó el resultado editorial.')
            if not envelope['ok']:
                raise EditorialError(envelope.get('error') or 'La operación editorial falló en Resolve.')
            if 'result' not in envelope:
                raise MCPError('Falta el resultado editorial de Resolve.')
            return envelope['result']
    except MCPError as error:
        if writing and dispatched:
            msg = str(error)
            if 'timed out after 60s' in msg:
                msg = (f'{error} ResolveMCP alcanzó su límite de 60s en run_script_unsafe. '
                       'Para secuencias extensas, configura DAVINCIFLOW_RESOLVE_TRANSPORT=legacy '
                       'o verifica el puente CPython 3.13.')
            raise EditorialError(
                f'{msg} El resultado de la escritura no está confirmado. '
                'No se ha reintentado: revisa la secuencia y el registro antes de repetir o deshacer.'
            ) from error
        raise EditorialError(f'{error} Comprueba Resolve Studio 21.1 y su conexión MCP.') from error
