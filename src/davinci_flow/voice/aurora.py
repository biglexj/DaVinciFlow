"""Generación y recuperación de audio de Aurora; sin reintentos facturables."""

import io
import json
from pathlib import Path
import uuid
import wave

from davinci_flow.user_data import user_data_dir
from davinci_flow.voice.account import AuroraAccount, endpoint
from davinci_flow.voice.aurora_http import AuroraError, json_request, request
from davinci_flow.voice.catalog import PROVIDER_NAMES, normalize_catalog, provider_id, voice_cost


class AuroraVoiceClient:
    def __init__(self, account=None, directory=None):
        self.account = account or AuroraAccount()
        self.directory = Path(directory) if directory else user_data_dir() / 'voice'
        self.access = None
        self.pending_id = None
        self.pending_provider = 'gemini'
        self.pending_voice = None

    def _headers(self):
        return {'Authorization': 'Bearer ' + self.account.token()}

    def refresh_access(self):
        self.access = None
        headers = self._headers()
        self.account.refresh_profile_avatar(headers)
        self._read_pending()
        try:
            value = json_request('GET', endpoint() + '?action=access', headers=headers)
        except AuroraError as error:
            if error.status == 401:
                self.account.invalidate()
            raise
        if (value.get('user', {}).get('id') != self.account.user['id'] or not isinstance(value.get('voices'), list)
                or type(value.get('balance')) is not int or value['balance'] < 0):
            raise AuroraError(502, 'invalid-response')
        self.access = normalize_catalog(value)
        return self.access

    def _pending_path(self):
        if not self.account.user:
            raise AuroraError(401, 'authentication-required')
        return self.directory / ('pending-' + str(uuid.UUID(self.account.user['id'])) + '.json')

    def _read_pending(self):
        try:
            value = json.loads(self._pending_path().read_text(encoding='utf-8'))
            self.pending_id = str(uuid.UUID(value['request_id']))
            self.pending_provider = provider_id(value.get('provider', 'gemini'))
            self.pending_voice = value.get('voice_id')
            if self.pending_provider not in PROVIDER_NAMES:
                raise ValueError()
        except FileNotFoundError:
            self.pending_id = None
            self.pending_provider, self.pending_voice = 'gemini', None
        except (ValueError, KeyError, TypeError):
            raise AuroraError(0, 'invalid-pending', 'No se pudo leer la solicitud pendiente de esta cuenta.') from None

    def _remember(self, identifier, provider='gemini', voice=None):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._pending_path()
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'request_id': identifier, 'provider': provider, 'voice_id': voice}), encoding='utf-8')
        temporary.replace(path)
        self.pending_id = identifier
        self.pending_provider, self.pending_voice = provider, voice

    def _forget(self):
        self._pending_path().unlink(missing_ok=True)
        self.pending_id = None
        self.pending_provider, self.pending_voice = 'gemini', None

    def generate(self, text, voice_id, provider='gemini'):
        if not text.strip() or len(text.strip()) > 10_000:
            raise AuroraError(400, 'invalid-text', 'Escribe entre 1 y 10.000 caracteres.')
        headers = self._headers()
        self._read_pending()
        if self.pending_id:
            raise AuroraError(409, 'pending-request', 'Recupera primero la generación pendiente; no se iniciará otra automáticamente.')
        provider = provider_id(provider)
        if provider not in PROVIDER_NAMES:
            raise AuroraError(400, 'provider-unavailable')
        engine = None
        if self.access and 'engines' in self.access:
            engine = next((e for e in self.access['engines'] if e['id'] == provider and e['available']), None)
            if engine is None or not any(v['id'] == voice_id and v['provider'] == provider and v['ready'] for v in self.access['voices']):
                raise AuroraError(400, 'voice-unavailable')
        elif provider != 'gemini':
            raise AuroraError(400, 'provider-unavailable', 'Actualiza el acceso para consultar este proveedor.')
        identifier = str(uuid.uuid4())
        payload = {'request_id': identifier, 'text': text.strip(), 'voice_id': voice_id, 'provider': provider}
        if self.access:
            payload['max_cost'] = voice_cost(text, engine['rate'] if engine else self.access.get('rate'), self.access.get('internal', False))
        self._remember(identifier, provider, voice_id)
        timeout = 3615 if provider == 'qwen' else 210
        try:
            result = request('POST', endpoint(), payload, headers=headers, timeout=timeout)
        except AuroraError as error:
            if error.status in (401, 402, 403) or error.code == 'rate-changed':
                self.access = None
            if error.status == 401:
                self.account.invalidate()
            if error.status in (400, 402, 403, 413) or error.code in {'voice-unavailable', 'synthesis-failed', 'generation-failed', 'rate-changed'}:
                self._forget()
            raise
        return self._save(result, identifier)

    def recover(self):
        headers = self._headers()
        self._read_pending()
        if not self.pending_id:
            raise AuroraError(404, 'not-found')
        identifier = self.pending_id
        try:
            result = request('GET', endpoint() + '?action=result&request_id=' + identifier, headers=headers, timeout=60)
        except AuroraError as error:
            if error.status == 401:
                self.access = None
                self.account.invalidate()
            if error.code in {'not-found', 'generation-failed'}:
                self._forget()
            raise
        return self._save(result, identifier)

    def _save(self, result, identifier):
        status, headers, content = result
        if status == 202:
            raise AuroraError(202, 'processing', 'Aurora aún está procesando esta solicitud. Puedes recuperarla de nuevo sin volver a generar.')
        provider = headers.get('x-voice-provider')
        if (headers.get('x-request-id') != identifier or provider != self.pending_provider
                or (headers.get('x-voice-id') is not None and self.pending_voice is not None and headers['x-voice-id'] != self.pending_voice)
                or headers.get('content-type', '').split(';')[0] not in {'audio/wav', 'audio/x-wav'}):
            raise AuroraError(502, 'invalid-audio')
        try:
            with wave.open(io.BytesIO(content), 'rb') as audio:
                if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                    raise ValueError()
            cost = int(headers['x-cost-credits'])
            if cost < 0:
                raise ValueError()
        except (ValueError, KeyError, EOFError, wave.Error):
            raise AuroraError(502, 'invalid-audio') from None
        folder = self.directory / 'generated' / str(uuid.UUID(self.account.user['id']))
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (identifier + '.wav')
        temporary = path.with_suffix('.part')
        try:
            temporary.write_bytes(content)
            temporary.replace(path)
            path.with_suffix('.json').write_text(json.dumps({'request_id': identifier, 'cost_credits': cost,
                'provider': provider, 'voice_id': self.pending_voice, 'user_id': self.account.user['id']}), encoding='utf-8')
        finally:
            temporary.unlink(missing_ok=True)
        self._forget()
        return path

    def logout(self):
        revoked = self.account.logout()
        self.access, self.pending_id = None, None
        return revoked
