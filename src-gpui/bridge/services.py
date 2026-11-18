"""Adaptador de servicios: preferencias, credenciales, IA, actualizaciones y catálogos.

Cada operación es explícita y devuelve un único sobre JSON. Las operaciones de lectura
no modifican el proyecto; las de escritura (credencial y preferencias) guardan en las
mismas rutas estándar que usa la aplicación de Flet, sin tocar la instalación estable.
"""
from contextlib import redirect_stdout
import json
import sys
from protocol import read_request

PREFIX = 'DAVINCI_FLOW_GPUI='

READ_OPERATIONS = {'settings', 'scan_models', 'assistant', 'release', 'sfx_catalog', 'templates', 'align'}
WRITE_OPERATIONS = {'save_key', 'save_settings', 'insert_markers'}


def parse_arguments(argv):
    values = {}
    for item in argv:
        if '=' not in item:
            raise ValueError('Argumento no válido para el puente de servicios.')
        key, _, raw = item.partition('=')
        values[key] = raw
    return values


def read_settings(provider_override=None):
    from davinci_flow.ai.credentials import has_provider_api_key
    from davinci_flow.ai.model_catalog import capability_for
    from davinci_flow.ai.providers.base import MINIMAX_MODELS, provider_names, provider_info
    from davinci_flow.editorial.preferences import Preferences

    preferences = Preferences.load()
    provider = provider_override or str(getattr(preferences, 'provider', 'gemini') or 'gemini')
    definition = provider_info(provider)
    model = preferences.model if provider == preferences.provider else definition.default_model
    models = list(MINIMAX_MODELS) if provider == 'minimax' else []
    capability = capability_for(provider, model, [])
    return {
        'provider': provider,
        'model': model,
        'has_key': has_provider_api_key(provider),
        'providers': list(provider_names()),
        'models': models,
        'capability': {
            'long_context': bool(getattr(capability, 'long_context', False)),
            'context_label': str(getattr(capability, 'context_label', '') or ''),
        },
        'preferences': {
            'mode': preferences.mode,
            'format': preferences.format,
            'density': preferences.density,
            'direction': preferences.direction,
            'track_mode': getattr(preferences, 'track_mode', 'triple'),
            'batch_size': getattr(preferences, 'batch_size', '20'),
        },
    }


def scan_models():
    from davinci_flow.ai.client import list_available_gemini_model_info
    from davinci_flow.ai.credentials import has_gemini_api_key

    if not has_gemini_api_key():
        raise ValueError('Configura la clave API de Gemini para consultar el catálogo de modelos.')
    models = list_available_gemini_model_info(use_fallback=False)
    return {'models': [info.model_id for info in models]}


def assistant(prompt):
    from davinci_flow.ai.providers.factory import build_text_provider
    from davinci_flow.editorial.preferences import Preferences

    preferences = Preferences.load()
    provider = build_text_provider(preferences.provider, preferences.model)
    return {'text': provider.generate_text(prompt=prompt)}


def release():
    from davinci_flow.updater.checker import check_github_release

    found = check_github_release()
    if found is None:
        return {'release': None}
    return {
        'release': {
            'version': found.version,
            'is_newer': bool(found.is_newer),
            'published_at': found.published_at or '',
            'notes': found.sanitized_notes,
            'download_url': found.download_url,
            'page_url': found.release_page_url,
        }
    }


def sfx_catalog():
    from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS

    return {
        'assets': [
            {
                'id': asset.id,
                'name': asset.name,
                'category': asset.category,
                'duration_seconds': asset.duration_seconds,
                'recommended_gain_db': asset.recommended_gain_db,
            }
            for asset in DEFAULT_SFX_ASSETS
        ]
    }


def templates():
    from davinci_flow.editorial.sources import scan_installed

    diagnostics = []
    from dataclasses import asdict
    catalog = {template.id: template for template in scan_installed(diagnostics=diagnostics)}
    return {
        'templates': [
            asdict(template) for template in catalog.values()
        ],
        'diagnostics': diagnostics,
    }


def align(arguments):
    """Alinea y corrige los subtítulos con el guion y el glosario indicados."""
    import json

    from davinci_flow.ai.aligner import ScriptAligner, parse_glossary_str
    from davinci_flow.editorial.preferences import Preferences
    from davinci_flow.subtitles.model import SubtitleCue

    raw_cues = arguments.get('cues') or '[]'
    try:
        payload = json.loads(raw_cues) if isinstance(raw_cues, str) else raw_cues
    except json.JSONDecodeError:
        raise ValueError('Los subtítulos recibidos no son válidos.') from None
    if not isinstance(payload, list) or not payload:
        raise ValueError('No hay subtítulos para procesar con IA.')

    fps = float(arguments.get('fps') or 24.0)
    cues = []
    for item in payload:
        cues.append(SubtitleCue(
            text=str(item.get('text', '')),
            start_frame=float(item.get('start_frame', 0.0)),
            end_frame=float(item.get('end_frame', 0.0)),
            track_index=int(item.get('track_index', 1)),
        ))

    preferences = Preferences.load()
    from davinci_flow.ai.providers.factory import build_text_provider
    aligner = ScriptAligner(client=build_text_provider(preferences.provider, preferences.model))
    glossary = parse_glossary_str(arguments.get('glossary', ''))
    result = aligner.align_and_correct(
        cues=cues,
        original_script=arguments.get('script', ''),
        glossary=glossary,
        detect_markers=arguments.get('detect_markers', 'true') != 'false',
    )
    return {
        'cues': [cue.text for cue in result.corrected_cues],
        'markers': [
            {
                'frame': marker.frame,
                'color': marker.color,
                'name': marker.name,
                'note': marker.note,
            }
            for marker in result.markers
        ],
        'corrections': len(result.corrections),
        'summary': result.summary,
        'fps': fps,
    }


def insert_markers(arguments):
    """Inserta en la línea de tiempo activa los marcadores generados por la IA."""
    import json

    from davinci_flow.ai.aligner import TimelineMarker
    from davinci_flow.editorial import resolve_bridge
    from davinci_flow.resolve import connect_to_resolve
    from davinci_flow.resolve.marker_writer import ResolveMarkerWriter
    from dataclasses import asdict

    saved = arguments.get('snapshot')
    if not isinstance(saved, dict) or saved.get('source') != 'resolve' or not saved.get('timeline_id') or not saved.get('project_id'):
        raise ValueError('Los marcadores requieren una captura identificada de Resolve.')
    current, _ = resolve_bridge.read_resolve(track=saved['track'], first=saved['first'], last=saved['last'])
    if json.loads(json.dumps(asdict(current), allow_nan=False)) != saved:
        raise ValueError('El montaje cambió desde la captura. Vuelve a capturar y generar los marcadores.')

    raw = arguments.get('markers') or '[]'
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        raise ValueError('Los marcadores recibidos no son válidos.') from None
    if not isinstance(payload, list) or not payload:
        raise ValueError('No hay marcadores para insertar.')
    markers = [
        TimelineMarker(
            frame=float(item.get('frame', 0.0)),
            color=str(item.get('color', 'Cyan')),
            name=str(item.get('name', 'Punto Clave')),
            note=str(item.get('note', '')),
        )
        for item in payload
    ]
    import math
    maximum = max(cue['end_frame'] for cue in saved['cues']) - saved['origin']
    if any(not math.isfinite(marker.frame) or marker.frame > maximum for marker in markers):
        raise ValueError('Hay marcadores fuera del intervalo de la captura.')
    session = connect_to_resolve()
    if str(session.project.GetUniqueId()) != saved['project_id'] or str(session.timeline.GetUniqueId()) != saved['timeline_id']:
        raise ValueError('El proyecto o montaje activo cambió antes de insertar.')
    inserted = ResolveMarkerWriter(session.timeline).apply_markers(markers)
    if inserted != len(markers):
        raise ValueError(f'Resolve confirmó {inserted} de {len(markers)} marcadores. Comprueba el resultado antes de repetir.')
    return {'inserted': inserted}


def save_key(provider, key):
    from davinci_flow.ai.credentials import save_provider_api_key

    if provider not in {'gemini', 'minimax'}:
        raise ValueError(f"Proveedor de IA desconocido: '{provider}'.")
    if not key.strip():
        raise ValueError('La clave API no puede quedar vacía.')
    path = save_provider_api_key(provider, key.strip())
    return {'saved': True, 'provider': provider, 'path': str(path)}


def save_settings(arguments):
    from davinci_flow.editorial.preferences import Preferences

    preferences = Preferences.load()
    if 'model' in arguments and arguments['model'].strip():
        preferences.model = arguments['model'].strip()
    if 'provider' in arguments and arguments['provider'].strip():
        preferences.provider = arguments['provider'].strip()
    for field in ('mode', 'format', 'density', 'direction', 'track_mode', 'batch_size'):
        if field in arguments and (field == 'direction' or arguments[field]):
            setattr(preferences, field, arguments[field])
    preferences.save()
    return read_settings()


def execute(operation, arguments):
    if operation in READ_OPERATIONS:
        if operation == 'settings':
            return read_settings(arguments.get('provider'))
        if operation == 'scan_models':
            return scan_models()
        if operation == 'assistant':
            prompt = arguments.get('prompt', '').strip()
            if not prompt:
                raise ValueError('Escribe una consulta para el asistente.')
            return assistant(prompt)
        if operation == 'release':
            return release()
        if operation == 'sfx_catalog':
            return sfx_catalog()
        if operation == 'align':
            return align(arguments)
        return templates()
    if operation == 'save_key':
        return save_key(arguments.get('provider', ''), arguments.get('key', ''))
    if operation == 'save_settings':
        return save_settings(arguments)
    if operation == 'insert_markers':
        return insert_markers(arguments)
    raise ValueError('Operación de servicios no admitida.')


def main():
    try:
        with redirect_stdout(sys.stderr):
            operation, arguments = read_request(parse_arguments)
            result = execute(operation, arguments)
        envelope = {'ok': True, 'result': result}
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    print(PREFIX + json.dumps(envelope, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
