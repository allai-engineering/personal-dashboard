"""Remembered-login tests use generated-looking fixtures, never real credentials."""
import base64
import hashlib
import http.client
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import types
import unittest
from unittest import mock

import server
import test_hosted_server as hosted


class RememberAuthTests(unittest.TestCase):
    FIXTURE_PASSWORD = b'fixture-only-password-75f9d0e10a2b4e4e8d3cfb27a61c209a'
    FIXTURE_SALT = bytes.fromhex('1fc478ade9b0332c8e52b8ba4f5d5bef66a0d3869e327ca2f90de9507cbb0b37')
    FIXTURE_KEY = bytes.fromhex('ab30cb372062ff3f6765f311a6f3a1e6b388df6ef38a152eadb3552c85d37b3f')
    FIXTURE_TIME = 1800000000

    @classmethod
    def setUpClass(cls):
        cls.fixture_digest = hashlib.pbkdf2_hmac('sha256', cls.FIXTURE_PASSWORD, cls.FIXTURE_SALT, 600000)
        cls.rotated_digest = hashlib.pbkdf2_hmac('sha256', b'fixture-only-rotated-36fa2cb0d5154d31891cc7e518e7aa67', cls.FIXTURE_SALT, 600000)

    def setUp(self):
        hosted.HostedServerTests.setUp(self)
        self.password = self.FIXTURE_PASSWORD
        self.auth = server.PasswordAuth(self.user, self.fixture_digest, self.FIXTURE_SALT, self.FIXTURE_KEY)
        self.header = 'Basic ' + base64.b64encode(self.user + b':' + self.password).decode()

    start_http = hosted.HostedServerTests.start_http
    request = hosted.HostedServerTests.request

    def signed_cookie(self, expiry):
        token = str(expiry) + '.' + 'b7' * 16
        return server.SESSION_COOKIE + '=' + token + '.' + self.auth.signature(token)

    def login(self, web):
        status, headers, body = self.request(web, '/', [self.header])
        self.assertEqual(status, 200)
        self.assertIn('Set-Cookie', headers)
        self.assertNotIn(self.password, body)
        return headers['Set-Cookie']

    def test_pbkdf_password_verifier_and_private_file_loader(self):
        auth_file = Path(self.tmp.name) / 'fixture-auth.json'
        auth_file.write_text(json.dumps({'username': self.user.decode(),
            'password_pbkdf2_sha256': self.fixture_digest.hex(), 'salt': self.FIXTURE_SALT.hex(),
            'session_key': self.FIXTURE_KEY.hex()}))
        auth_file.chmod(0o640)
        original_fstat = os.fstat

        def root_stat(fd):
            info = original_fstat(fd)
            return types.SimpleNamespace(st_mode=info.st_mode, st_uid=0, st_size=info.st_size)

        with mock.patch.object(server.os, 'fstat', side_effect=root_stat):
            auth = server.load_auth(auth_file)
        self.assertIsInstance(auth, server.PasswordAuth)
        self.assertTrue(server.authenticated([self.header], auth))
        self.assertFalse(auth.verify(self.user, b'wrong-fixture-password'))
        self.assertFalse(auth.verify(b'other-fixture-user', self.password))

    def test_cookie_attributes_and_no_credential_material(self):
        web = self.start_http()
        issued = self.login(web)
        cookies = SimpleCookie()
        cookies.load(issued)
        self.assertEqual(set(cookies), {server.SESSION_COOKIE})
        cookie = cookies[server.SESSION_COOKIE]
        self.assertTrue(server.SESSION_COOKIE.startswith('__Host-'))
        self.assertEqual(cookie['path'], '/')
        self.assertEqual(cookie['domain'], '')
        self.assertEqual(cookie['max-age'], str(30 * 24 * 60 * 60))
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        for private in (self.password.decode(), self.header, base64.b64encode(self.user + b':' + self.password).decode(),
                        self.fixture_digest.hex(), self.FIXTURE_KEY.hex(), self.FIXTURE_SALT.hex()):
            self.assertNotIn(private, issued)

    def test_cookie_only_new_connections_do_not_reissue_or_renew(self):
        web = self.start_http()
        with mock.patch.object(server.time, 'time', return_value=self.FIXTURE_TIME):
            issued = self.login(web)
        cookie = issued.split(';', 1)[0]
        with mock.patch.object(server.time, 'time', return_value=self.FIXTURE_TIME + 3600), \
             mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as password_check, \
             mock.patch.object(self.auth, 'cookie', wraps=self.auth.cookie) as issue_cookie:
            # The existing helper creates and closes a new connection for every request.
            for path, authorization in (('/', ()), ('/accounts.mjs', ()), ('/api/snapshot', ()), ('/', [self.header])):
                with self.subTest(path=path, basic_also_present=bool(authorization)):
                    status, headers, body = self.request(web, path, authorization, headers=[('Cookie', cookie)])
                    self.assertEqual(status, 200)
                    self.assertNotIn('Set-Cookie', headers)
                    self.assertNotIn(self.password, body)
            password_check.assert_not_called()
            issue_cookie.assert_not_called()

    def test_expiry_and_signed_future_cookie_fail_closed(self):
        with mock.patch.object(server.time, 'time', return_value=self.FIXTURE_TIME):
            for remaining in (-1, 0, server.SESSION_SECONDS + 1):
                with self.subTest(remaining=remaining):
                    self.assertFalse(self.auth.remembered([self.signed_cookie(self.FIXTURE_TIME + remaining)]))
            for remaining in (1, server.SESSION_SECONDS):
                with self.subTest(remaining=remaining):
                    self.assertTrue(self.auth.remembered([self.signed_cookie(self.FIXTURE_TIME + remaining)]))

    def test_cookie_tampering_other_key_and_password_rotation_reject(self):
        with mock.patch.object(server.time, 'time', return_value=self.FIXTURE_TIME):
            cookie = self.signed_cookie(self.FIXTURE_TIME + 3600)
            prefix, value = cookie.split('=', 1)
            expiry, nonce, signature = value.split('.')
            tampered = [str(int(expiry) + 1) + '.' + nonce + '.' + signature,
                        expiry + '.' + ('0' if nonce[0] != '0' else '1') + nonce[1:] + '.' + signature,
                        expiry + '.' + nonce + '.' + ('0' if signature[0] != '0' else '1') + signature[1:]]
            for value in tampered:
                self.assertFalse(self.auth.remembered([prefix + '=' + value]))
            alternatives = [server.PasswordAuth(self.user, self.fixture_digest, self.FIXTURE_SALT, b'X' * 32),
                            server.PasswordAuth(self.user, self.rotated_digest, self.FIXTURE_SALT, self.FIXTURE_KEY),
                            server.PasswordAuth(b'other-fixture-user', self.fixture_digest, self.FIXTURE_SALT, self.FIXTURE_KEY)]
            for changed in alternatives:
                self.assertFalse(changed.remembered([cookie]))

    def test_malformed_and_repeated_cookie_headers_or_names_reject_over_http(self):
        web = self.start_http()
        cookie = self.login(web).split(';', 1)[0]
        for headers in ([('Cookie', cookie), ('Cookie', cookie)],
                        [('Cookie', cookie + '; ' + cookie)],
                        [('Cookie', cookie), ('Cookie', 'other=fixture')],
                        [('Cookie', server.SESSION_COOKIE + '=invalid')],
                        [('Cookie', server.SESSION_COOKIE + '=' + 'x' * 8193)]):
            with self.subTest(kind='repeated' if len(headers) > 1 else 'one_header'):
                web.snapshot_cache.get.reset_mock()
                status, response_headers, _ = self.request(web, '/api/snapshot', headers=headers)
                self.assertEqual(status, 401)
                self.assertNotIn('Set-Cookie', response_headers)
                web.snapshot_cache.get.assert_not_called()
        self.assertEqual(self.request(web, '/api/snapshot', headers=[('Cookie', 'other=fixture; ' + cookie)])[0], 200)

    def test_valid_cookie_preserves_origin_host_and_read_only_guards(self):
        web = self.start_http()
        cookie = self.login(web).split(';', 1)[0]
        base = [('Cookie', cookie)]
        rejected = [('/api/snapshot', 'GET', [('Origin', 'https://other.invalid')], 403),
                    ('/api/snapshot', 'GET', [('Origin', web.public_origin), ('Origin', web.public_origin)], 403),
                    ('/api/snapshot', 'GET', [('Sec-Fetch-Site', 'cross-site')], 403),
                    ('/api/snapshot', 'GET', [('Host', 'other.invalid')], 403),
                    ('/api/refresh', 'POST', [], 405),
                    ('/api/snapshot?unexpected=1', 'GET', [], 404)]
        for path, method, extra, expected in rejected:
            with self.subTest(path=path, method=method, extra=extra):
                web.snapshot_cache.get.reset_mock()
                status, headers, _ = self.request(web, path, method=method, headers=base + extra)
                self.assertEqual(status, expected)
                self.assertNotIn('Set-Cookie', headers)
                web.snapshot_cache.get.assert_not_called()
        # Also reject a single wrong Host, rather than only the duplicate Host case above.
        connection = http.client.HTTPConnection('127.0.0.1', web.server_port, timeout=3)
        try:
            connection.putrequest('GET', '/api/snapshot', skip_host=True)
            connection.putheader('Host', 'other.invalid')
            connection.putheader('Cookie', cookie)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
        finally:
            connection.close()
        web.snapshot_cache.get.assert_not_called()

    def test_shared_password_failure_limit_and_valid_cookie_bypass(self):
        web = self.start_http()
        cookie = self.login(web).split(';', 1)[0]
        real_kdf = server.hashlib.pbkdf2_hmac
        with mock.patch.object(server.time, 'monotonic', return_value=100.0), \
             mock.patch.object(server.hashlib, 'pbkdf2_hmac', wraps=real_kdf) as kdf:
            for attempt in range(10):
                wrong = 'Basic ' + base64.b64encode(('fixture-user-' + str(attempt) + ':wrong-fixture').encode()).decode()
                self.assertEqual(self.request(web, '/', [wrong])[0], 401)
            self.assertEqual(kdf.call_count, 10)
            # A new HTTP connection and even the correct password share the exhausted gate.
            self.assertEqual(self.request(web, '/', [self.header])[0], 401)
            self.assertEqual(kdf.call_count, 10)
            status, headers, _ = self.request(web, '/api/snapshot', headers=[('Cookie', cookie)])
            self.assertEqual(status, 200)
            self.assertNotIn('Set-Cookie', headers)
            self.assertEqual(kdf.call_count, 10)
        with mock.patch.object(server.time, 'monotonic', return_value=160.0):
            self.assertEqual(self.request(web, '/', [self.header])[0], 200)

    def test_external_top_level_navigation_still_requires_auth_and_is_home_only(self):
        web = self.start_http()
        cookie = self.login(web).split(';', 1)[0]
        navigation = [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'),
                      ('Sec-Fetch-Dest', 'document')]
        status, headers, body = self.request(web, '/', headers=navigation)
        self.assertEqual(status, 200)
        self.assertIn(b'<form', body)
        self.assertNotIn(b'anonymous-test-account', body)
        self.assertNotIn('Set-Cookie', headers)
        status, headers, _ = self.request(web, '/', headers=[('Cookie', cookie)] + navigation)
        self.assertEqual(status, 200)
        self.assertNotIn('Set-Cookie', headers)
        rejected = [('/api/snapshot', navigation), ('/accounts.mjs', navigation),
                    ('/?unexpected=1', navigation),
                    ('/', [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'),
                           ('Sec-Fetch-Dest', 'iframe')]),
                    ('/', [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'cors'),
                           ('Sec-Fetch-Dest', 'document')]),
                    ('/', navigation + [('Origin', web.public_origin)]),
                    ('/', navigation + [('Origin', 'https://other.invalid')]),
                    ('/', navigation + [('Host', 'other.invalid')])]
        for path, extra in rejected:
            with self.subTest(path=path, extra=extra):
                status, headers, _ = self.request(web, path, headers=[('Cookie', cookie)] + extra)
                self.assertEqual(status, 403)
                self.assertNotIn('Set-Cookie', headers)
        web.snapshot_cache.get.assert_not_called()

    def test_duplicate_fetch_headers_reject_valid_cookie_navigation(self):
        web = self.start_http()
        cookie = self.login(web).split(';', 1)[0]
        for site in ('cross-site', 'same-origin'):
            fetch = [('Sec-Fetch-Site', site), ('Sec-Fetch-Mode', 'navigate'), ('Sec-Fetch-Dest', 'document')]
            for repeated in fetch:
                with self.subTest(site=site, duplicate=repeated[0]):
                    status, headers, _ = self.request(web, '/', headers=[('Cookie', cookie)] + fetch + [repeated])
                    self.assertEqual(status, 403)
                    self.assertNotIn('Set-Cookie', headers)
        web.snapshot_cache.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
