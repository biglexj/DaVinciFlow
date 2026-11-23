"""Contrato del catálogo nativo de Voice Studio y consumo por motor."""

from davinci_flow.voice.aurora_http import AuroraError

PROVIDER_NAMES = {'piper': 'Piper', 'pocket_tts': 'Pocket TTS', 'gemini': 'Gemini Cloud',
                  'qwen': 'Qwen · Voz clonada', 'minimax': 'MiniMax'}
ALIASES = {'pocket-tts': 'pocket_tts', 'pocket': 'pocket_tts', 'xtts': 'qwen',
           'qwen_tts': 'qwen', 'vozely': 'qwen', 'minimax_tts': 'minimax', 'minimax-tts': 'minimax'}


def provider_id(value):
    return ALIASES.get(value, value) if isinstance(value, str) else None


def valid_rate(rate):
    return (isinstance(rate, dict) and rate.get('is_active') is True
            and rate.get('unit') in {'100_chars', '200_chars'}
            and type(rate.get('rate_credits')) is int and rate['rate_credits'] >= 0)


def normalize_catalog(access):
    """Mantiene compatibilidad con el catálogo Gemini de la primera versión."""
    modern = access.get('catalog_version') == 2
    voices = []
    for value in access.get('voices', []):
        if not isinstance(value, dict):
            continue
        provider = provider_id(value.get('provider', 'gemini' if not modern else None))
        if (provider in PROVIDER_NAMES and isinstance(value.get('id'), str) and value['id']
                and isinstance(value.get('name'), str) and value['name']):
            voices.append({**value, 'provider': provider, 'ready': value.get('ready', not modern) is True})
    engines = []
    if modern:
        if not isinstance(access.get('engines'), list):
            raise AuroraError(502, 'invalid-response')
        seen = set()
        for value in access['engines']:
            if not isinstance(value, dict):
                raise AuroraError(502, 'invalid-response')
            key = provider_id(value.get('id'))
            if key not in PROVIDER_NAMES or key in seen:
                raise AuroraError(502, 'invalid-response')
            seen.add(key)
            if (type(value.get('available')) is not bool
                    or not isinstance(value.get('name'), str) or not value['name']
                    or (value['available'] and not access.get('internal') and not valid_rate(value.get('rate')))):
                raise AuroraError(502, 'invalid-response')
            engines.append({**value, 'id': key, 'rate': value.get('rate')})
    else:
        if not valid_rate(access.get('rate')):
            raise AuroraError(502, 'invalid-response')
        # El contrato antiguo solo admite Gemini, aunque llegue otra voz ajena.
        voices = [voice for voice in voices if voice['provider'] == 'gemini']
        if voices:
            engines = [{'id': 'gemini', 'name': PROVIDER_NAMES['gemini'], 'rate': access['rate'],
                        'available': any(v['ready'] for v in voices), 'timeout_seconds': 180}]
    return {**access, 'engines': engines, 'voices': voices}


def voice_cost(text, rate, internal=False):
    if internal:
        return 0
    if not valid_rate(rate):
        raise AuroraError(503, 'rate-unavailable')
    count = len(text.strip())
    unit = 200 if rate['unit'] == '200_chars' else 100
    return ((count + unit - 1) // unit) * rate['rate_credits']
