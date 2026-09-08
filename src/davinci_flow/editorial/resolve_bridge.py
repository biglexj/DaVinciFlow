"""Operaciones editoriales cerradas por stdin/stdout; la ABI de Resolve vive en CPython."""

from dataclasses import asdict
from functools import lru_cache
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

from davinci_flow.editorial.model import EditorialError, Proposal, Snapshot, Template
from davinci_flow.generation.record import GenerationExecutionRecord
from davinci_flow.subtitles.model import SubtitleCue

OPERATIONS = {'capture', 'titles', 'apply', 'undo'}
RESULT_PREFIX = 'DAVINCI_FLOW_RESULT='
SOURCE = Path(__file__).resolve().parents[2]


def _environment():
    env = os.environ.copy()
    env['PYTHONPATH'] = str(SOURCE) + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUTF8'] = '1'
    return env


@lru_cache(maxsize=1)
def resolve_python():
    configured = os.environ.get('DAVINCIFLOW_RESOLVE_PYTHON')
    root = SOURCE.parent
    executable = 'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
    candidates = [Path(configured)] if configured else [root / '.venv-resolve' / executable, root / '.venv' / executable]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        probe = subprocess.run([str(candidate), '-c',
            'import platform,sys; print(platform.python_implementation(),sys.version_info[:2],sys.maxsize>2**32)'],
            capture_output=True, text=True, timeout=10, env=_environment(),
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if probe.returncode == 0 and probe.stdout.strip() == 'CPython (3, 13) True':
            return str(candidate)
    raise EditorialError('Falta el puente CPython 3.13 de 64 bits. Ejecuta scripts/setup-desktop.ps1 '
                         'o configura DAVINCIFLOW_RESOLVE_PYTHON con su ejecutable.')


def request(operation, **parameters):
    if operation not in OPERATIONS:
        raise EditorialError('Operación de Resolve no admitida.')
    # Las escrituras no se interrumpen por un timeout ni se reintentan automáticamente.
    timeout = 90 if operation in {'capture', 'titles'} else None
    try:
        result = subprocess.run([resolve_python(), '-m', 'davinci_flow.editorial.resolve_bridge'],
            input=json.dumps({'operation': operation, 'parameters': parameters}, ensure_ascii=False),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
            env=_environment(), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as error:
        raise EditorialError('Resolve no respondió a la lectura en 90 segundos. Comprueba su estado.') from error
    except OSError as error:
        raise EditorialError(f'No se pudo iniciar el puente de Resolve: {error}') from error
    messages = [line[len(RESULT_PREFIX):] for line in result.stdout.splitlines() if line.startswith(RESULT_PREFIX)]
    if result.returncode != 0 or len(messages) != 1:
        raise EditorialError(f'El puente de Resolve terminó sin una respuesta válida (código {result.returncode}). '
                             'Comprueba Resolve y su intérprete antes de repetir la operación.')
    try:
        envelope = json.loads(messages[0])
        if not envelope['ok']:
            raise EditorialError(envelope['error'])
        return envelope['result']
    except (ValueError, KeyError, TypeError) as error:
        raise EditorialError('Respuesta del puente de Resolve inválida.') from error


def read_resolve(track=1, first=1, last=120):
    data = request('capture', track=track, first=first, last=last)
    raw = data['snapshot']
    raw['cues'] = tuple(SubtitleCue(**cue) for cue in raw['cues'])
    raw['cuts'] = tuple(tuple(cut) for cut in raw.get('cuts', ()))
    return Snapshot(**raw), tuple(Template(**t) for t in data['templates'])


def read_titles():
    return tuple(Template(**t) for t in request('titles'))


def apply(proposal):
    proposal.validate(require_review=True)
    with TemporaryDirectory(prefix='davinci-flow-review-') as directory:
        path = Path(directory) / 'proposal.json'
        proposal.save(path)
        return GenerationExecutionRecord.from_dict(request('apply', proposal_path=str(path)))


def undo():
    return GenerationExecutionRecord.from_dict(request('undo'))


def dispatch(operation, parameters):
    """Solo se ejecuta en el auxiliar; ningún objeto nativo cruza el proceso."""
    if operation not in OPERATIONS:
        raise EditorialError('Operación de Resolve no admitida.')
    from davinci_flow.resolve import connect_to_resolve
    from davinci_flow.editorial.sources import capture, media_pool_catalog
    from davinci_flow.editorial.service import apply_reviewed, record_path_for, undo_reviewed
    # Validar la revisión antes de conectar; el servicio vuelve a verificar la secuencia.
    proposal = Proposal.load(parameters['proposal_path']) if operation == 'apply' else None
    if proposal:
        proposal.validate(require_review=True)
    session = connect_to_resolve()
    if operation in {'capture', 'titles'}:
        templates, _ = media_pool_catalog(session.project.GetMediaPool())
        catalog = [asdict(t) for t in templates]
        if operation == 'titles':
            return catalog
        snapshot = capture(session, **parameters)
        return {'snapshot': asdict(snapshot), 'templates': catalog}
    if operation == 'apply':
        s = proposal.snapshot
        return apply_reviewed(proposal, session, record_path_for(s.project_id, s.timeline_id)).to_dict()
    return undo_reviewed(session, record_path_for(str(session.project.GetUniqueId()),
                                                  str(session.timeline.GetUniqueId()))).to_dict()


def main():
    try:
        if platform.python_implementation() != 'CPython' or sys.version_info[:2] != (3, 13) or sys.maxsize <= 2**32:
            raise EditorialError('El auxiliar de Resolve necesita CPython 3.13 de 64 bits.')
        payload = json.load(sys.stdin)
        result = dispatch(payload['operation'], payload.get('parameters', {}))
        envelope = {'ok': True, 'result': result}
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    print(RESULT_PREFIX + json.dumps(envelope, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
