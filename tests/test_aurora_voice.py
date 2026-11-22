import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import io
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit
import uuid
import wave

from davinci_flow.voice import account as module
from davinci_flow.voice.account import AuroraAccount, validate_callback
from davinci_flow.voice.aurora import AuroraVoiceClient
from davinci_flow.voice.aurora_http import AuroraError
from davinci_flow.voice.secure_store import SecureStore

UID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
CONFIG = {'url':'https://identity.example', 'public_key':'sb_publishable_fixture'}
TOKENS = {'access_token':'access-fixture', 'refresh_token':'refresh-fixture', 'expires_in':3600}


class MemoryStore:
    def __init__(self): self.data = {}
    def read(self, name): return copy.deepcopy(self.data.get(name))
    def write(self, name, value): self.data[name] = copy.deepcopy(value)
    def remove(self, name): self.data.pop(name, None)
    def exists(self, name): return name in self.data


def wave_bytes():
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(24000)
        audio.writeframes(b'\x00\x00' * 240)
    return output.getvalue()


class AuroraAccountTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.account = AuroraAccount(self.store)
        self.account._config = dict(CONFIG)

    def test_pkce_challenge_and_attempt_are_saved_before_opening_browser(self):
        with patch.object(module, 'register_protocol') as register:
            url = self.account.begin_login('google')
        query = parse_qs(urlsplit(url).query)
        pending = self.store.read('pending')
        challenge = base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).decode().rstrip('=')
        self.assertEqual(query['code_challenge'], [challenge])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertIn('app=' + module.scheme(), query['redirect_to'][0])
        self.assertNotIn('verifier', url)
        register.assert_called_once()

    def test_callback_rejects_other_app_tokens_duplicates_or_fragment(self):
        for uri in ['prisma://auth/callback?code=abc', module.scheme()+'://auth/callback?access_token=abc',
                    module.scheme()+'://auth/callback?code=a&code=b', module.scheme()+'://auth/callback?code=a#token']:
            with self.subTest(uri=uri), self.assertRaises(AuroraError): validate_callback(uri)

    def test_code_exchange_is_once_and_verifies_identity(self):
        with patch.object(module, 'register_protocol'): self.account.begin_login()
        pending = self.store.read('pending')
        self.store.write('callback', {'code':'single-use-code', 'attempt':pending['attempt']})
        with patch.object(module, 'json_request', side_effect=[TOKENS, {'id':UID,'email':'fixture@example.test'}]) as network:
            self.assertEqual(self.account.complete_login()['id'], UID)
        self.assertEqual(network.call_args_list[0].args[2]['code_verifier'], pending['verifier'])
        self.assertFalse(self.store.exists('pending'))
        self.assertFalse(self.store.exists('callback'))
        self.assertTrue(self.store.exists('session'))
        with patch.object(module, 'json_request') as network:
            with self.assertRaises(AuroraError): self.account.complete_login()
        network.assert_not_called()

    def test_wrong_attempt_cannot_exchange_and_never_contacts_provider(self):
        with patch.object(module, 'register_protocol'): self.account.begin_login()
        self.store.write('callback', {'code':'code', 'attempt':'other'})
        with patch.object(module, 'json_request') as network:
            with self.assertRaises(AuroraError): self.account.complete_login()
        network.assert_not_called()

    def test_callback_from_old_attempt_cannot_replace_current_attempt(self):
        self.store.write('pending', {'attempt':'a'*32,'expires':time.time()+600})
        with patch.object(module, 'SecureStore', return_value=self.store):
            with self.assertRaises(AuroraError): module.accept_callback(module.scheme()+'://auth/callback?code=old&flow='+'b'*32)
            self.assertFalse(self.store.exists('callback'))
            module.accept_callback(module.scheme()+'://auth/callback?code=current&flow='+'a'*32)
            self.assertEqual(self.store.read('callback')['code'], 'current')

    def test_concurrent_refresh_rotates_only_once(self):
        self.account._save_pair(TOKENS)
        self.account._pair['expires'] = time.time() - 10
        self.account.user = {'id':UID}
        def respond(method, url, *args, **kwargs):
            return TOKENS if 'grant_type=refresh_token' in url else {'id':UID}
        with patch.object(module, 'json_request', side_effect=respond) as network, ThreadPoolExecutor(4) as workers:
            results = list(workers.map(lambda _:self.account.token(), range(4)))
        self.assertEqual(results, ['access-fixture'] * 4)
        self.assertEqual(sum('refresh_token' in c.args[1] for c in network.call_args_list), 1)

    def test_rejected_refresh_clears_local_session_without_fallback(self):
        self.account._save_pair(TOKENS)
        self.account._pair['expires'] = 0
        self.account.user = {'id':UID}
        with patch.object(module, 'json_request', side_effect=AuroraError(400,'invalid_grant')):
            with self.assertRaises(AuroraError): self.account.token()
        self.assertIsNone(self.account.user)
        self.assertFalse(self.store.exists('session'))

    def test_logout_is_local_even_if_remote_revocation_fails(self):
        self.account._save_pair(TOKENS)
        with patch.object(module, 'request', side_effect=AuroraError(0,'network')):
            self.assertFalse(self.account.logout())
        self.assertIsNone(self.account.user)
        self.assertFalse(self.store.exists('session'))

    def test_profile_avatar_refresh_uses_the_verified_account(self):
        original = 'https://identity.example/original.png'
        uploaded = 'https://aurora.example/uploaded.png'
        self.account.user = {'id': UID, 'avatar_url': original}
        headers = {'Authorization': 'Bearer fixture-token'}
        with patch.object(module, 'json_request', side_effect=[
            {'user': {'id': UID, 'image': uploaded}},
            {'user': {'id': str(uuid.uuid4()), 'image': original}},
            AuroraError(503, 'service-unavailable'),
        ]) as network:
            for _ in range(3):
                self.account.refresh_profile_avatar(headers)
                self.assertEqual(self.account.user['profile_avatar_url'], uploaded)
        self.assertTrue(network.call_args.args[1].endswith('/api/auth/session'))
        self.assertEqual(network.call_args.kwargs['headers'], headers)
        self.assertEqual(self.account.user['avatar_url'], original)

    @unittest.skipUnless(os.name == 'nt', 'DPAPI requiere Windows')
    def test_windows_vault_is_encrypted_and_bound_to_its_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = SecureStore(Path(tmp)/'dev')
            first.write('session', {'refresh_token':'secret-fixture'})
            content = (first.directory/'session.bin').read_bytes()
            self.assertNotIn(b'secret-fixture', content)
            self.assertEqual(first.read('session'), {'refresh_token':'secret-fixture'})
            second = SecureStore(Path(tmp)/'stable'); second.directory.mkdir()
            (second.directory/'session.bin').write_bytes(content)
            with self.assertRaises(Exception): second.read('session')


class AuroraVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.account = SimpleNamespace(user={'id':UID}, token=Mock(return_value='fixture-token'), invalidate=Mock())
        self.client = AuroraVoiceClient(self.account, Path(self.temp.name))

    def test_unknown_result_is_not_resubmitted_and_can_be_recovered(self):
        with patch('davinci_flow.voice.aurora.request', side_effect=AuroraError(0,'network')) as network:
            with self.assertRaises(AuroraError): self.client.generate('Hola', 'gemini-test')
            identifier = self.client.pending_id
            with self.assertRaises(AuroraError): self.client.generate('Hola', 'gemini-test')
        network.assert_called_once()
        result = (200, {'x-request-id':identifier,'x-voice-provider':'gemini','content-type':'audio/wav','x-cost-credits':'3'}, wave_bytes())
        with patch('davinci_flow.voice.aurora.request', return_value=result) as network:
            path = self.client.recover()
        self.assertEqual(network.call_args.args[0], 'GET')
        self.assertEqual(path.read_bytes(), wave_bytes())
        self.assertIsNone(self.client.pending_id)
        self.assertFalse(list(Path(self.temp.name).glob('pending*.json')))

    def test_wrong_provider_is_not_saved_and_keeps_recovery_available(self):
        def response(*args, **kwargs):
            identifier = self.client.pending_id
            return 200, {'x-request-id':identifier,'x-voice-provider':'minimax','content-type':'audio/wav','x-cost-credits':'3'}, wave_bytes()
        with patch('davinci_flow.voice.aurora.request', side_effect=response):
            with self.assertRaises(AuroraError): self.client.generate('Hola','gemini-test')
        self.assertTrue(self.client.pending_id)
        self.assertFalse(list(Path(self.temp.name).rglob('*.wav')))

    def test_pending_request_is_isolated_by_account(self):
        self.client._remember(str(uuid.uuid4()))
        self.account.user = {'id':'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'}
        self.client._read_pending()
        self.assertIsNone(self.client.pending_id)

    def test_server_rejection_does_not_leave_generator_ready_with_stale_balance(self):
        self.client.access = {'balance':60, 'rate':{'rate_credits':3,'unit':'100_chars','is_active':True}}
        with patch('davinci_flow.voice.aurora.request', side_effect=AuroraError(402,'insufficient-credits')):
            with self.assertRaises(AuroraError): self.client.generate('Hola','gemini-test')
        self.assertIsNone(self.client.access)
        self.assertIsNone(self.client.pending_id)
