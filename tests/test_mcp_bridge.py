"""Contrato MCP, ausencia de reintentos y captura de transiciones de Resolve 21.1."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from davinci_flow.editorial import mcp_bridge, resolve_bridge
from davinci_flow.editorial.model import EditorialError
from davinci_flow.editorial.sources import capture
from davinci_flow.resolve.mcp_client import MCPError, ResolveMCP, find_mcp_executable
from tests.test_editorial import sample
from tests.test_editorial_writer import setup
from davinci_flow.editorial.service import apply_reviewed, undo_reviewed


# Proceso real que habla JSON-RPC por tuberías, sin abrir Resolve en las pruebas.
SERVER = r'''
import json, sys, time
mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    if 'id' not in request:
        continue
    result = {'serverInfo': {'name': 'davinci_resolve', 'version': '21.1'}}
    if request['method'] == 'tools/call':
        if mode == 'eof':
            break
        if mode == 'timeout':
            time.sleep(2)
        result = {'content': [{'type': 'text', 'text': json.dumps({'running': True})}]}
        if mode == 'embedded-error':
            result['content'][0]['text'] = json.dumps({'error': 'Error dentro del script'})
        if mode == 'tool-error':
            result['isError'] = True
        if mode == 'malformed':
            result['content'][0]['text'] = 'not json'
        if mode == 'missing-content':
            result['content'] = None
    print('Diagnóstico nativo', flush=True)
    print(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/message', 'params': {}}), flush=True)
    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)
'''


class MCPTransportTests(unittest.TestCase):
    def server(self, mode='ok'):
        original = subprocess.Popen
        def spawn(command, **kwargs):
            return original([sys.executable, '-u', '-c', SERVER, mode], **kwargs)
        return patch('davinci_flow.resolve.mcp_client.subprocess.Popen', side_effect=spawn)

    def test_real_pipes_ignore_noise_correlate_responses_and_close(self):
        with self.server():
            with ResolveMCP(Path('test-server')) as client:
                self.assertEqual(client.server_info['version'], '21.1')
                self.assertTrue(client.status()['running'])
                self.assertTrue(client.status()['running'])
            self.assertIsNotNone(client.process.poll())
            self.assertFalse(any(thread.is_alive() for thread in client.threads))

    def test_eof_timeout_and_both_error_envelopes_fail(self):
        for mode in ('eof', 'timeout', 'embedded-error', 'tool-error', 'malformed', 'missing-content'):
            with self.subTest(mode=mode), self.server(mode):
                with ResolveMCP(Path('test-server')) as client:
                    with self.assertRaises(MCPError):
                        client.call_tool('get_resolve_status', timeout=.05 if mode == 'timeout' else 2)
                self.assertIsNotNone(client.process.poll())

    def test_bad_explicit_path_is_not_silently_ignored(self):
        with patch.dict(os.environ, {'DAVINCIFLOW_RESOLVE_MCP': '/missing/ResolveMCP'}):
            with self.assertRaises(MCPError):
                find_mcp_executable()


class BridgeSelectionTests(unittest.TestCase):
    def test_auto_prefers_official_mcp_without_calling_legacy_python(self):
        with patch.dict(os.environ, {'DAVINCIFLOW_RESOLVE_TRANSPORT': 'auto'}), \
             patch.object(resolve_bridge, 'find_mcp_executable', return_value=Path('ResolveMCP.exe')), \
             patch.object(mcp_bridge, 'request', return_value={'native': True}) as native, \
             patch.object(resolve_bridge, 'legacy_request') as legacy:
            self.assertEqual(resolve_bridge.request('capture', first=2), {'native': True})
        native.assert_called_once_with(Path('ResolveMCP.exe'), 'capture', {'first': 2})
        legacy.assert_not_called()

    def test_auto_only_falls_back_when_executable_is_absent(self):
        with patch.dict(os.environ, {'DAVINCIFLOW_RESOLVE_TRANSPORT': 'auto'}), \
             patch.object(resolve_bridge, 'find_mcp_executable', return_value=None), \
             patch.object(resolve_bridge, 'legacy_request', return_value=[]) as legacy:
            self.assertEqual(resolve_bridge.request('titles'), [])
        legacy.assert_called_once_with('titles')

    def test_native_failure_never_retries_on_legacy(self):
        with patch.object(resolve_bridge, 'selected_transport', return_value=('mcp', Path('ResolveMCP'))), \
             patch.object(mcp_bridge, 'request', side_effect=EditorialError('Sin confirmación')) as native, \
             patch.object(resolve_bridge, 'legacy_request') as legacy:
            with self.assertRaises(EditorialError):
                resolve_bridge.request('undo')
        native.assert_called_once()
        legacy.assert_not_called()

    def test_explicit_mcp_and_invalid_mode_do_not_fall_back(self):
        for mode in ('mcp', 'typo'):
            with patch.dict(os.environ, {'DAVINCIFLOW_RESOLVE_TRANSPORT': mode}), \
                 patch.object(resolve_bridge, 'find_mcp_executable', return_value=None):
                with self.assertRaises(EditorialError):
                    resolve_bridge.selected_transport()

    def test_explicit_legacy_does_not_probe_mcp(self):
        with patch.dict(os.environ, {'DAVINCIFLOW_RESOLVE_TRANSPORT': 'legacy'}), \
             patch.object(resolve_bridge, 'find_mcp_executable') as find:
            self.assertEqual(resolve_bridge.selected_transport(), ('legacy', None))
        find.assert_not_called()


class NativeEditorialTests(unittest.TestCase):
    def test_injected_session_never_reconnects_to_native_dll(self):
        session, _, _ = setup()
        with patch('davinci_flow.resolve.connect_to_resolve') as connect:
            data = resolve_bridge.dispatch('capture', {}, session=session)
        self.assertEqual(data['snapshot']['timeline_id'], 'timeline-1')
        connect.assert_not_called()

    def test_failed_preflight_does_not_claim_a_write_was_sent(self):
        with patch.object(mcp_bridge, 'ResolveMCP') as factory:
            client = factory.return_value.__enter__.return_value
            client.status.side_effect = MCPError('Sin sesión')
            with self.assertRaises(EditorialError) as caught:
                mcp_bridge.request(Path('ResolveMCP'), 'undo', {})
        self.assertNotIn('escritura', str(caught.exception))
        client.call_tool.assert_not_called()

    def test_unreviewed_proposal_never_starts_native_server(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'proposal.json'
            sample().save(path)
            with patch.object(mcp_bridge, 'ResolveMCP') as client:
                with self.assertRaises(EditorialError):
                    mcp_bridge.request(Path('ResolveMCP'), 'apply', {'proposal_path': str(path)})
            client.assert_not_called()

    def test_script_injects_session_and_treats_parameters_as_data(self):
        parameters = {'track': 1, 'first': 2, 'last': 3}
        with patch.object(mcp_bridge, 'ResolveMCP') as factory:
            client = factory.return_value.__enter__.return_value
            client.status.return_value = {'running': True}
            client.call_tool.return_value = {'result': {'ok': True, 'result': {'captured': True}}}
            self.assertEqual(mcp_bridge.request(Path('ResolveMCP'), 'capture', parameters), {'captured': True})
        args = client.call_tool.call_args
        self.assertEqual(args.args[0], 'run_script_unsafe')
        script = args.args[1]['script']
        self.assertIn('connect_to_resolve(resolve)', script)
        self.assertIn('session=_flow_session', script)
        self.assertIn('sys.path[:] = _flow_path', script)
        compile(script, '<mcp>', 'exec')

    def test_lost_write_response_is_explicitly_uncertain_and_not_retried(self):
        with patch.object(mcp_bridge, 'ResolveMCP') as factory:
            client = factory.return_value.__enter__.return_value
            client.status.return_value = {'running': True}
            client.call_tool.side_effect = MCPError('Canal cerrado')
            with self.assertRaisesRegex(EditorialError, 'no está confirmado'):
                mcp_bridge.request(Path('ResolveMCP'), 'undo', {})
        client.call_tool.assert_called_once()

    def test_business_rejection_is_not_reported_as_success(self):
        with patch.object(mcp_bridge, 'ResolveMCP') as factory:
            client = factory.return_value.__enter__.return_value
            client.status.return_value = {'running': True}
            client.call_tool.return_value = {'result': {'ok': False, 'error': 'La secuencia cambió'}}
            with self.assertRaisesRegex(EditorialError, 'secuencia cambió'):
                mcp_bridge.request(Path('ResolveMCP'), 'capture', {})


class TransitionCaptureTests(unittest.TestCase):
    def session(self):
        s = sample().snapshot
        item = Mock()
        item.GetType.return_value = 'transition'
        item.GetUniqueId.return_value = 'transition-1'
        item.GetName.return_value = 'Fundido'
        item.GetStart.return_value, item.GetEnd.return_value = 86400, 86412
        item.GetLeftOffset.return_value = item.GetRightOffset.return_value = None
        timeline = Mock()
        timeline.GetTrackCount.side_effect = lambda kind: 1 if kind == 'video' else 0
        timeline.GetTrackName.return_value = 'Video 1'
        timeline.GetItemListInTrack.return_value = [item]
        timeline.GetUniqueId.return_value = s.timeline_id
        timeline.GetName.return_value = s.timeline
        timeline.GetStartFrame.return_value = s.origin
        timeline.GetSetting.side_effect = {'timelineFrameRate': s.fps, 'timelineResolutionWidth': s.width,
                                           'timelineResolutionHeight': s.height}.get
        project = Mock()
        project.GetName.return_value, project.GetUniqueId.return_value = s.project, s.project_id
        return SimpleNamespace(timeline=timeline, project=project), item

    def test_transition_has_no_offsets_but_changes_still_invalidate_fingerprint(self):
        session, item = self.session()
        with patch('davinci_flow.editorial.sources.ResolveSubtitleReader') as reader:
            reader.return_value.read_track.return_value = sample().snapshot.cues
            before = capture(session)
            self.assertEqual(before.cuts[0][6:], (None, 'transition', 'Fundido'))
            item.GetEnd.return_value += 1
            self.assertNotEqual(before.fingerprint, capture(session).fingerprint)
            item.GetEnd.return_value -= 1
            item.GetName.return_value = 'Empujar'
            self.assertNotEqual(before.fingerprint, capture(session).fingerprint)

    def test_missing_offsets_on_media_fail_closed(self):
        session, item = self.session()
        item.GetType.return_value = 'video'
        with patch('davinci_flow.editorial.sources.ResolveSubtitleReader') as reader:
            reader.return_value.read_track.return_value = sample().snapshot.cues
            with self.assertRaisesRegex(EditorialError, 'offsets'):
                capture(session)

    def test_generator_has_no_offsets_but_captured_in_fingerprint(self):
        session, item = self.session()
        item.GetType.return_value = 'generator'
        item.GetName.return_value = 'Color sólido'
        item.GetMediaPoolItem.return_value = None
        with patch('davinci_flow.editorial.sources.ResolveSubtitleReader') as reader:
            reader.return_value.read_track.return_value = sample().snapshot.cues
            snap = capture(session)
            self.assertEqual(snap.cuts[0][6:], (None, 'generator', 'Color sólido'))


class NativeNameCompatibilityTests(unittest.TestCase):
    def test_legacy_names_are_reused_and_reverted_without_duplicates(self):
        session, pool, proposal = setup()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'record.json'
            record = apply_reviewed(proposal, session, path)
            generated = [item for values in session.timeline.items.values() for item in values
                         if item.GetName().startswith('DF__')]
            self.assertEqual(len(generated), 3)
            for item in generated:
                self.assertNotIn(':', item.GetName())
                item.SetName(item.GetName().replace('__', '::'))
            apply_reviewed(proposal, session, path)
            self.assertEqual(pool.count, 3)
            self.assertEqual(undo_reviewed(session, path).status, 'reverted')


if __name__ == '__main__':
    unittest.main()
