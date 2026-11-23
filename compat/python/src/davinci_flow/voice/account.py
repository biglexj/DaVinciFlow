"""Adaptación Python del login Provider/PKCE de Ely Intelligence y Aurora Hub."""

import base64
import hashlib
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from davinci_flow.user_data import is_development, user_data_dir
from davinci_flow.voice.aurora_http import AuroraError, json_request, request
from davinci_flow.voice.secure_store import SecureStore


def scheme():
    return 'davinciflow-dev' if is_development() else 'davinciflow'


def endpoint():
    origin = os.environ.get('DAVINCIFLOW_AURORA_URL', 'https://biglexj.com').rstrip('/') if is_development() else 'https://biglexj.com'
    parsed = urlsplit(origin)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise AuroraError(0, 'invalid-origin')
    if parsed.scheme != 'https' and not (is_development() and parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost'}):
        raise AuroraError(0, 'invalid-origin')
    return origin + '/api/creador/voice-studio/native'


def _https_avatar(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme == 'https' and parsed.hostname and parsed.username is None:
        return value
    return None


def validate_callback(url):
    parsed = urlsplit(url)
    values = parse_qs(parsed.query, keep_blank_values=True)
    if (parsed.scheme != scheme() or parsed.netloc != 'auth' or parsed.path != '/callback' or parsed.fragment
            or set(values) != {'code', 'flow'} or len(values['code']) != 1 or len(values['flow']) != 1
            or not re.fullmatch(r'[a-f0-9]{32}', values['flow'][0])
            or not re.fullmatch(r'[A-Za-z0-9._~-]{1,2048}', values['code'][0])):
        raise AuroraError(400, 'invalid-callback', 'El retorno de inicio de sesión no es válido para esta versión.')
    return values['code'][0], values['flow'][0]


def accept_callback(url):
    code, attempt = validate_callback(url)
    store = SecureStore(user_data_dir() / 'account')
    pending = store.read('pending')
    if not pending or pending.get('expires', 0) <= time.time() or pending.get('attempt') != attempt:
        raise AuroraError(400, 'login-expired', 'El inicio de sesión ha caducado. Vuelve a iniciarlo desde la app.')
    store.write('callback', {'code': code, 'attempt': pending['attempt']})


def register_protocol():
    if os.name != 'nt':
        raise AuroraError(0, 'unsupported-platform', 'El retorno nativo todavía requiere Windows.')
    import winreg
    if getattr(sys, 'frozen', False):
        arguments = [sys.executable, '--auth-callback', '%1']
    else:
        root = Path(__file__).resolve().parents[3]
        python = Path(sys.executable).with_name('pythonw.exe')
        callback_script = root / 'bridge/auth_callback.py'
        arguments = [str(python if python.is_file() else sys.executable), str(callback_script), '%1']
    base = 'Software\\Classes\\' + scheme()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'URL:DaVinci Flow Aurora login')
        winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\shell\\open\\command') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, subprocess.list2cmdline(arguments[:-1]) + ' "%1"')


class AuroraAccount:
    def __init__(self, store=None):
        self.store = store or SecureStore(user_data_dir() / 'account')
        self.user = None
        self._pair = None
        self._config = None
        self._lock = threading.RLock()

    def config(self):
        if self._config is None:
            value = json_request('GET', endpoint() + '?action=config')
            config = value.get('auth', {})
            url, public_key = config.get('url', ''), config.get('public_key', '')
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise AuroraError(502, 'invalid-auth-config')
            if public_key.startswith('sb_publishable_'):
                valid = True
            else:
                try:
                    part = public_key.split('.')[1]
                    import json
                    valid = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))).get('role') == 'anon'
                except (ValueError, IndexError, TypeError):
                    valid = False
            if not valid:
                raise AuroraError(502, 'invalid-auth-config')
            self._config = {'url': url.rstrip('/'), 'public_key': public_key}
        return self._config

    def begin_login(self, provider='google'):
        if provider not in {'google', 'discord'}:
            raise AuroraError(400, 'invalid-provider')
        with self._lock:
            config = self.config()
            verifier = secrets.token_urlsafe(64)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            attempt = secrets.token_hex(16)
            self.store.remove('callback')
            self.store.write('pending', {'attempt': attempt, 'verifier': verifier,
                'expires': time.time() + 600, 'config': config, 'endpoint': endpoint()})
            register_protocol()
            return config['url'] + '/auth/v1/authorize?' + urlencode({'provider': provider,
                'redirect_to': 'https://biglexj.com/auth/native-return?' + urlencode({'app': scheme(), 'flow': attempt}),
                'code_challenge': challenge, 'code_challenge_method': 'S256'})

    def cancel_login(self):
        with self._lock:
            self.store.remove('pending')
            self.store.remove('callback')

    def complete_login(self):
        with self._lock:
            pending, callback = self.store.read('pending'), self.store.read('callback')
            self.store.remove('callback')
            if (not pending or not callback or callback.get('attempt') != pending.get('attempt')
                    or pending.get('expires', 0) <= time.time() or pending.get('endpoint') != endpoint()):
                self.store.remove('pending')
                raise AuroraError(400, 'login-expired', 'El retorno no corresponde a un inicio de sesión pendiente.')
            self._config = pending['config']
            # Un código es de un solo uso: no repetir el canje tras un resultado incierto.
            self.store.remove('pending')
            tokens = json_request('POST', self._config['url'] + '/auth/v1/token?grant_type=pkce',
                {'auth_code': callback['code'], 'code_verifier': pending['verifier']},
                headers={'apikey': self._config['public_key']})
            self._save_pair(tokens)
            return self._verify()

    def _save_pair(self, value):
        if (not isinstance(value.get('access_token'), str) or not value['access_token']
                or not isinstance(value.get('refresh_token'), str) or not value['refresh_token']
                or not isinstance(value.get('expires_in'), (int, float))
                or not math.isfinite(value['expires_in']) or value['expires_in'] <= 0):
            raise AuroraError(502, 'invalid-session')
        pair = {'access_token': value['access_token'], 'refresh_token': value['refresh_token'],
                'expires': time.time() + value['expires_in'], 'config': self.config(), 'endpoint': endpoint()}
        self.store.write('session', pair)
        self._pair = pair

    def _verify(self):
        try:
            user = json_request('GET', self._pair['config']['url'] + '/auth/v1/user', headers={
                'apikey': self._pair['config']['public_key'], 'Authorization': 'Bearer ' + self._pair['access_token']})
            if not user.get('id'):
                raise AuroraError(401, 'session-expired')
            previous = self.user or {}
            self.user = {'id': user['id'], 'email': user.get('email', '')}
            if previous.get('id') == user['id'] and previous.get('profile_avatar_url'):
                self.user['profile_avatar_url'] = previous['profile_avatar_url']
            metadata = user.get('user_metadata')
            if isinstance(metadata, dict):
                avatar = _https_avatar(metadata.get('avatar_url')) or _https_avatar(metadata.get('picture'))
                if avatar:
                    self.user['avatar_url'] = avatar
            return self.user
        except AuroraError as error:
            self.user = None
            if error.status in (400, 401, 403):
                self.store.remove('session')
                self._pair = None
            raise

    def refresh_profile_avatar(self, headers):
        user = self.user
        if not user:
            return
        try:
            response = json_request('GET', urljoin(endpoint(), '/api/auth/session'), headers=headers, timeout=5)
        except AuroraError:
            return
        profile = response.get('user')
        if self.user is user and isinstance(profile, dict) and profile.get('id') == user['id']:
            user['profile_avatar_url'] = _https_avatar(profile.get('image'))

    def restore(self):
        with self._lock:
            self._pair = self.store.read('session')
            if not self._pair:
                self.user = None
                return None
            if self._pair.get('endpoint') != endpoint():
                self.user = None
                self._pair = None
                raise AuroraError(401, 'session-expired')
            self._config = self._pair['config']
            if self._pair.get('expires', 0) < time.time() + 60:
                self._refresh()
            return self._verify()

    def _refresh(self):
        try:
            value = json_request('POST', self._config['url'] + '/auth/v1/token?grant_type=refresh_token',
                {'refresh_token': self._pair['refresh_token']}, headers={'apikey': self._config['public_key']})
            self._save_pair(value)
        except AuroraError as error:
            if error.status in (400, 401, 403):
                self.store.remove('session')
                self._pair, self.user = None, None
            raise

    def token(self):
        with self._lock:
            if self._pair is None or self.user is None:
                self.restore()
            if self._pair is None:
                raise AuroraError(401, 'authentication-required')
            if self._pair['expires'] < time.time() + 60:
                self._refresh()
                self._verify()
            return self._pair['access_token']

    def logout(self):
        with self._lock:
            revoked = True
            try:
                if self._pair:
                    request('POST', self._pair['config']['url'] + '/auth/v1/logout?scope=local', headers={
                        'apikey': self._pair['config']['public_key'], 'Authorization': 'Bearer ' + self._pair['access_token']})
            except AuroraError:
                revoked = False
            finally:
                self._pair, self.user = None, None
                self.store.remove('session')
                self.cancel_login()
            return revoked

    def invalidate(self):
        with self._lock:
            self.store.remove('session')
            self._pair, self.user = None, None
