import argparse
import base64
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

import server


class HostedServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'snapshot.json'
        self.now = dt.datetime(2026, 10, 29, 21, tzinfo=dt.timezone.utc)
        self.value = {'schema': 'cpa-account-dashboard-v1', 'status': 'ok', 'read_only': True,
            'generation_requests_sent': 0, 'observed_at_utc': self.now.isoformat(),
            'inventory': {'status': 'ok', 'complete': True, 'listed_accounts': 1},
            'accounts': [{'id': 'anonymous-test-account'}], 'observed_orphans': []}
        self.path.write_text(json.dumps(self.value))
        self.cache = server.SnapshotFile(self.path, lambda: self.now)
        self.user = b'dashboard'
        self.password = b'test-only-token-not-a-production-password'
        self.auth = self.user, hashlib.sha256(self.password).digest()
        self.header = 'Basic ' + base64.b64encode(self.user + b':' + self.password).decode()

    def test_file_read_uses_observation_time_not_read_time(self):
        first = self.cache.get()
        self.assertFalse(first['cache']['stale'])
        self.now += dt.timedelta(seconds=75)
        later = self.cache.get()
        self.assertEqual(later['cache']['fetched_at_utc'], first['cache']['fetched_at_utc'])
        self.assertEqual(later['cache']['age_seconds'], 75)
        self.now += dt.timedelta(seconds=45)
        self.assertTrue(self.cache.get()['cache']['stale'])
        self.assertIsNone(self.cache.get()['cache']['last_error'])

    def test_broken_file_keeps_last_valid_snapshot_and_freshness(self):
        first = self.cache.get()
        self.path.write_text('PRIVATE_MALFORMED_BODY')
        self.now += dt.timedelta(seconds=10)
        result = self.cache.get()
        self.assertEqual(result['accounts'], first['accounts'])
        self.assertEqual(result['cache']['fetched_at_utc'], first['cache']['fetched_at_utc'])
        self.assertTrue(result['cache']['stale'])
        self.assertEqual(result['cache']['last_error'], 'invalid_snapshot')
        self.assertNotIn('PRIVATE_MALFORMED_BODY', json.dumps(result))
        self.path.unlink()
        self.assertEqual(self.cache.get()['cache']['last_error'], 'file_unavailable')

    def test_first_missing_file_is_unavailable_not_an_empty_verified_registry(self):
        self.path.unlink()
        result = self.cache.get()
        self.assertEqual(result['status'], 'unavailable')
        self.assertFalse(result['inventory']['complete'])
        self.assertIsNone(result['observed_at_utc'])
        self.assertTrue(result['cache']['stale'])

    def test_invalid_schema_privacy_marker_and_timestamps_are_rejected(self):
        self.cache.get()
        for changes in ({'schema': 'other'}, {'read_only': False}, {'generation_requests_sent': 1},
                {'generation_requests_sent': False}, {'observed_at_utc': '2026-10-29T21:00:00'},
                {'observed_at_utc': None}, {'observed_at_utc': '2026-10-29T21:00:01Z'},
                {'status': 'invalid'}, {'additional': float('nan')}):
            with self.subTest(changes=changes):
                self.path.write_text(json.dumps({**self.value, **changes}))
                result = self.cache.get()
                self.assertEqual(result['cache']['last_error'], 'invalid_snapshot')
                self.assertEqual(result['accounts'], self.value['accounts'])
        self.path.write_text(json.dumps(self.value)[:-1] + ', "bad_number": 1e999}')
        self.assertEqual(self.cache.get()['cache']['last_error'], 'invalid_snapshot')
        self.path.write_text(json.dumps(self.value)[:-1] + ', "deep":' + '['*600 + '0' + ']'*600 + '}')
        self.assertEqual(self.cache.get()['cache']['last_error'], 'invalid_snapshot')
        self.assertEqual(self.cache.get()['accounts'], self.value['accounts'])

    def test_read_limit_and_special_files_fail_closed(self):
        with self.path.open('wb') as output:
            output.truncate(server.MAX_SNAPSHOT_BYTES + 1)
        self.assertEqual(self.cache.get()['cache']['last_error'], 'snapshot_size_limit')
        self.path.unlink()
        target = Path(self.tmp.name) / 'target.json'
        target.write_text(json.dumps(self.value))
        self.path.symlink_to(target)
        self.assertEqual(self.cache.get()['cache']['last_error'], 'file_unavailable')
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertEqual(self.cache.get()['cache']['last_error'], 'file_unavailable')

    def test_operations_snapshot_is_protected_allowlisted_data(self):
        import operations
        data = {'schema': operations.SCHEMA, 'read_only': True, 'collected_at': self.now.isoformat(),
                'balances': [operations.unavailable_balance(p, 'not_configured', self.now) for p in operations.PROVIDERS],
                'fleet': {'status': 'unavailable', 'observed_at': None, 'inventory_count': None, 'enrolled': None, 'machines': []}}
        path = self.path.parent/'operations.json'
        path.write_text(json.dumps(data))
        self.assertEqual(self.cache.get()['operations'], data)
        data['api_key'] = 'SECRET_SHOULD_NOT_PASS'
        path.write_text(json.dumps(data))
        result = self.cache.get()
        self.assertIsNone(result['operations'])
        self.assertNotIn('SECRET_SHOULD_NOT_PASS', json.dumps(result))
        path.unlink()
        self.assertIsNone(self.cache.get()['operations'])

    def test_file_mode_starts_without_collector_module(self):
        # The deployed web release intentionally contains no collector or SSH reader.
        (Path(self.tmp.name) / 'server.py').write_bytes(Path(server.__file__).read_bytes())
        (Path(self.tmp.name) / 'operations.py').write_bytes(Path(server.__file__).with_name('operations.py').read_bytes())
        (Path(self.tmp.name) / 'battery_schema.py').write_bytes(Path(server.__file__).with_name('battery_schema.py').read_bytes())
        (Path(self.tmp.name) / 'integrations.py').write_bytes(Path(server.__file__).with_name('integrations.py').read_bytes())
        (Path(self.tmp.name) / 'mail_subscriptions.py').write_bytes(Path(server.__file__).with_name('mail_subscriptions.py').read_bytes())
        (Path(self.tmp.name) / 'mail_secretary.py').write_bytes(Path(server.__file__).with_name('mail_secretary.py').read_bytes())
        code = '''import sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import server
web = types.SimpleNamespace(serve_forever=lambda: None)
server.DashboardServer = lambda *args, **kwargs: web
server.SnapshotCache = lambda: (_ for _ in ()).throw(AssertionError('collection requested'))
sys.argv = ['server.py', '--snapshot-file', sys.argv[2]]
server.main()
assert web.snapshot_cache.get()['read_only'] is True
assert 'collector' not in sys.modules
assert 'mac_battery' not in sys.modules
assert not Path(server.__file__).with_name('mac_battery.py').exists()
'''
        result = subprocess.run([sys.executable, '-I', '-c', code, self.tmp.name, str(self.path)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_origin_is_exact_https_and_requires_auth_at_startup(self):
        origin = server.public_origin('https://Dashboard.Example.test:8443/')
        self.assertEqual(origin, 'https://dashboard.example.test:8443')
        self.assertEqual(server.public_origin('https://example.test:443'), 'https://example.test')
        for candidate in ('http://example.test', 'https://*.example.test', 'https://user:pass@example.test',
                          'https://example.test/path', 'https://example.test?x=1', 'https://example.test#x',
                          ' https://example.test', 'https://example.test:99999'):
            with self.subTest(candidate=candidate), self.assertRaises(argparse.ArgumentTypeError):
                server.public_origin(candidate)
        with mock.patch.object(sys, 'argv', ['server.py', '--snapshot-file', str(self.path), '--public-origin', origin]), \
             mock.patch.object(server, 'DashboardServer') as constructor, mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit) as raised:
                server.main()
            self.assertEqual(raised.exception.code, 2)
            constructor.assert_not_called()
        host = ['dashboard.example.test:8443']
        self.assertTrue(server.allowed_request(host, [origin], 'same-origin', 8766, origin))
        self.assertTrue(server.allowed_request(['127.0.0.1:8766'], [], None, 8766, origin))
        for hosts, origins, site in ((['evil.test'], [], None), (host*2, [], None),
                (host, [origin, origin], None), (host, ['http://dashboard.example.test:8443'], None),
                (host, ['https://dashboard.example.test:8443.evil.test'], None), (host, [], 'cross-site'),
                (['127.0.0.1:8766'], [origin], 'same-origin')):
            self.assertFalse(server.allowed_request(hosts, origins, site, 8766, origin))

    def test_auth_file_permissions_and_shape(self):
        auth_file = Path(self.tmp.name) / 'auth.json'
        auth_file.write_text(json.dumps({'username': self.user.decode(), 'password_sha256': self.auth[1].hex()}))
        auth_file.chmod(0o640)
        original_stat = os.fstat
        def root_stat(fd):
            meta = original_stat(fd)
            return types.SimpleNamespace(st_mode=meta.st_mode, st_size=meta.st_size, st_uid=0)
        with mock.patch.object(server.os, 'fstat', side_effect=root_stat):
            self.assertEqual(server.load_auth(auth_file), self.auth)
            auth_file.chmod(0o644)
            with self.assertRaisesRegex(ValueError, '^auth-file must be'):
                server.load_auth(auth_file)
            auth_file.chmod(0o640)
            auth_file.write_text(json.dumps({'username': 'a', 'password_sha256': 'invalid'}))
            with self.assertRaises(ValueError):
                server.load_auth(auth_file)
        with mock.patch.object(server.os, 'fstat', return_value=types.SimpleNamespace(st_mode=0o100640, st_size=100, st_uid=123)):
            with self.assertRaises(ValueError):
                server.load_auth(auth_file)

    def test_auth_rejects_malformed_duplicate_and_wrong_credentials(self):
        self.assertTrue(server.authenticated([self.header], self.auth))
        wrong = 'Basic ' + base64.b64encode(self.user + b':wrong').decode()
        for headers in ([], [self.header, self.header], ['Bearer token'], ['Basic ???'],
                        ['Basic '+ 'A'*1025], ['Basic '+base64.b64encode(b'missing-colon').decode()],
                        [wrong], ['Basic '+base64.b64encode(b'other:'+self.password).decode()]):
            self.assertFalse(server.authenticated(headers, self.auth))

    def start_http(self):
        web = server.DashboardServer(('127.0.0.1', 0), server.Handler)
        web.public_origin = 'https://dashboard.example.test:8443'
        web.auth = self.auth
        web.snapshot_cache = mock.Mock(wraps=self.cache)
        thread = threading.Thread(target=web.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            web.shutdown()
            web.server_close()
            thread.join(2)
        self.addCleanup(cleanup)
        return web

    def request(self, web, path, authorization=(), method='GET', headers=()):
        connection = http.client.HTTPConnection('127.0.0.1', web.server_port, timeout=3)
        try:
            connection.putrequest(method, path, skip_host=True)
            connection.putheader('Host', 'dashboard.example.test:8443')
            for value in authorization:
                connection.putheader('Authorization', value)
            for key, value in headers:
                connection.putheader(key, value)
            connection.endheaders()
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_all_get_routes_require_auth_and_credentials_never_echo(self):
        web = self.start_http()
        for path in ('/', '/accounts.css', '/model.mjs', '/api/snapshot', '/api/refresh'):
            with self.subTest(path=path):
                status, headers, body = self.request(web, path)
                self.assertEqual(status, 401)
                self.assertTrue(headers['WWW-Authenticate'].startswith('Basic realm='))
                self.assertNotIn(b'anonymous-test-account', body)
                web.snapshot_cache.get.assert_not_called()
                status, headers, body = self.request(web, path, [self.header])
                self.assertEqual(status, 200)
                self.assertNotIn(self.password, body)
                self.assertNotIn(self.header, str(headers))
                web.snapshot_cache.get.reset_mock()
        status, _, body = self.request(web, '/api/snapshot', [self.header, self.header])
        self.assertEqual(status, 401)
        self.assertNotIn(self.password, body)
        web.snapshot_cache.get.assert_not_called()

    def test_auth_does_not_relax_origin_routes_or_methods(self):
        web = self.start_http()
        self.assertEqual(self.request(web, '/api/snapshot', [self.header], headers=[('Origin','https://evil.test')])[0], 403)
        self.assertEqual(self.request(web, '/api/snapshot?sql=anything', [self.header])[0], 404)
        self.assertEqual(self.request(web, '/%2e%2e/server.py', [self.header])[0], 404)
        self.assertEqual(self.request(web, '/api/refresh', method='POST')[0], 405)
        web.snapshot_cache.get.assert_not_called()

    def test_exhausted_worker_limit_closes_extra_request(self):
        web = server.DashboardServer(('127.0.0.1', 0), server.Handler)
        self.addCleanup(web.server_close)
        for _ in range(16):
            self.assertTrue(web.request_slots.acquire(blocking=False))
        request = mock.Mock()
        with mock.patch.object(web, 'shutdown_request') as close:
            web.process_request(request, ('127.0.0.1', 1234))
            close.assert_called_once_with(request)
        for _ in range(16):
            web.request_slots.release()


if __name__ == '__main__':
    unittest.main()
