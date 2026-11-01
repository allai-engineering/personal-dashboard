"""Password-only login contract; local fixture server and test credentials only."""
import base64
import hashlib
import http.client
from http.cookies import SimpleCookie
from html.parser import HTMLParser
import socket
import unittest
from unittest import mock
from urllib.parse import urlencode

import server
import test_remember_auth as remembered


class LoginPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms, self.inputs, self.links = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in ('form', 'input', 'link'):
            getattr(self, {'form': 'forms', 'input': 'inputs', 'link': 'links'}[tag]).append(dict(attrs))


class PasswordLoginTests(unittest.TestCase):
    FIXTURE_PASSWORD = remembered.RememberAuthTests.FIXTURE_PASSWORD
    FIXTURE_SALT = remembered.RememberAuthTests.FIXTURE_SALT
    FIXTURE_KEY = remembered.RememberAuthTests.FIXTURE_KEY
    setUpClass = classmethod(remembered.RememberAuthTests.setUpClass.__func__)
    setUp = remembered.RememberAuthTests.setUp
    start_http = remembered.RememberAuthTests.start_http
    request = remembered.RememberAuthTests.request

    def form(self, password=None):
        return urlencode({'password': (self.password if password is None else password).decode('utf-8')}).encode()

    def post(self, web, body=None, headers=None, *, path='/login', method='POST', host='dashboard.example.test:8443', end_input=False):
        body = self.form() if body is None else body
        if headers is None:
            headers = self.post_headers(web, body)
        connection = http.client.HTTPConnection('127.0.0.1', web.server_port, timeout=3)
        try:
            connection.putrequest(method, path, skip_host=True)
            connection.putheader('Host', host)
            for key, value in headers:
                connection.putheader(key, value)
            connection.endheaders(body)
            if end_input:
                connection.sock.shutdown(socket.SHUT_WR)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def post_headers(self, web, body):
        return [('Origin', web.public_origin), ('Content-Type', 'application/x-www-form-urlencoded'),
                ('Content-Length', str(len(body)))]

    def assert_no_challenge_or_private_echo(self, headers, body):
        self.assertNotIn('WWW-Authenticate', headers)
        self.assertNotIn(self.password, body)
        self.assertNotIn(self.header, str(headers))
        self.assertNotIn(self.fixture_digest.hex().encode(), body)
        self.assertNotIn(self.FIXTURE_KEY.hex().encode(), body)

    def test_unauthenticated_home_is_one_password_form_and_login_css_is_public(self):
        web = self.start_http()
        status, headers, body = self.request(web, '/')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/html'))
        self.assert_no_challenge_or_private_echo(headers, body)
        self.assertNotIn('Set-Cookie', headers)
        self.assertNotIn(b'anonymous-test-account', body)
        self.assertIn("form-action 'self'", headers['Content-Security-Policy'])
        parsed = LoginPage()
        parsed.feed(body.decode('utf-8'))
        self.assertEqual(len(parsed.forms), 1)
        self.assertEqual(parsed.forms[0].get('action'), '/login')
        self.assertEqual(parsed.forms[0].get('method', '').lower(), 'post')
        self.assertEqual(len(parsed.inputs), 1)
        self.assertEqual(parsed.inputs[0].get('name'), 'password')
        self.assertEqual(parsed.inputs[0].get('type'), 'password')
        self.assertFalse(parsed.inputs[0].get('value'))
        self.assertTrue(any(link.get('href') == '/login.css' for link in parsed.links))
        status, headers, body = self.request(web, '/login.css')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/css'))
        self.assertTrue(body)
        self.assert_no_challenge_or_private_echo(headers, body)
        web.snapshot_cache.get.assert_not_called()

    def test_protected_api_and_assets_keep_401_without_browser_basic_challenge(self):
        web = self.start_http()
        for path in ('/api/snapshot', '/api/refresh', '/accounts.mjs', '/accounts.css'):
            with self.subTest(path=path):
                status, headers, body = self.request(web, path)
                self.assertEqual(status, 401)
                self.assert_no_challenge_or_private_echo(headers, body)
                self.assertNotIn(b'anonymous-test-account', body)
        wrong = 'Basic ' + base64.b64encode(self.user + b':wrong-fixture').decode()
        status, headers, body = self.request(web, '/', [wrong])
        self.assertEqual(status, 401)
        self.assert_no_challenge_or_private_echo(headers, body)
        web.snapshot_cache.get.assert_not_called()

    def test_success_redirect_cookie_and_cookie_only_new_connection(self):
        web = self.start_http()
        status, headers, body = self.post(web)
        self.assertEqual(status, 303)
        self.assertEqual(headers.get('Location'), '/')
        self.assert_no_challenge_or_private_echo(headers, body)
        parsed = SimpleCookie()
        parsed.load(headers['Set-Cookie'])
        self.assertEqual(set(parsed), {server.SESSION_COOKIE})
        cookie = parsed[server.SESSION_COOKIE]
        self.assertEqual(cookie['path'], '/')
        self.assertEqual(cookie['domain'], '')
        self.assertEqual(cookie['max-age'], str(30 * 24 * 60 * 60))
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertNotIn(self.password.decode(), headers['Set-Cookie'])
        remembered_cookie = headers['Set-Cookie'].split(';', 1)[0]
        with mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
            status, headers, body = self.request(web, '/api/snapshot', headers=[('Cookie', remembered_cookie)])
            self.assertEqual(status, 200)
            self.assertIn(b'anonymous-test-account', body)
            self.assertNotIn('Set-Cookie', headers)
            verifier.assert_not_called()

    def test_existing_cookie_and_basic_compatibility_without_key_rotation(self):
        web = self.start_http()
        prior = self.auth.cookie().split(';', 1)[0]
        key = self.auth.session_key
        self.assertEqual(self.post(web)[0], 303)
        self.assertEqual(self.auth.session_key, key)
        self.assertEqual(self.request(web, '/', headers=[('Cookie', prior)])[0], 200)
        status, headers, _ = self.request(web, '/api/snapshot', headers=[('Cookie', prior)])
        self.assertEqual(status, 200)
        self.assertNotIn('Set-Cookie', headers)
        self.assertEqual(self.request(web, '/api/snapshot', [self.header])[0], 200)

    def test_wrong_password_has_fixed_generic_html_error_no_echo_or_cookie(self):
        web = self.start_http()
        responses = []
        for password in (b'PRIVATE-FIXTURE-WRONG-A-0eea3fb9', b'PRIVATE-FIXTURE-WRONG-B-c9ef28d0'):
            status, headers, body = self.post(web, self.form(password))
            self.assertEqual(status, 401)
            self.assertTrue(headers['Content-Type'].startswith('text/html'))
            self.assertIn(b'<form', body)
            self.assertNotIn(password, body)
            self.assertNotIn('Set-Cookie', headers)
            self.assert_no_challenge_or_private_echo(headers, body)
            responses.append(body)
        self.assertEqual(responses[0], responses[1])
        web.snapshot_cache.get.assert_not_called()

    def test_login_page_referrer_policy_allows_native_form_origin_but_api_stays_private(self):
        web = self.start_http()
        status, headers, _ = self.request(web, '/')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Referrer-Policy'], 'same-origin')
        status, headers, _ = self.post(web, self.form(b'wrong-fixture-for-referrer-check'))
        self.assertEqual(status, 401)
        self.assertTrue(headers['Content-Type'].startswith('text/html'))
        self.assertEqual(headers['Referrer-Policy'], 'same-origin')
        for authorization, expected in (((), 401), ([self.header], 200)):
            status, headers, _ = self.request(web, '/api/snapshot', authorization)
            self.assertEqual(status, expected)
            self.assertEqual(headers['Referrer-Policy'], 'no-referrer')

    def test_wrong_cached_basic_shows_form_and_does_not_override_posted_password(self):
        web = self.start_http()
        wrong = 'Basic ' + base64.b64encode(self.user + b':wrong-cached-fixture').decode()
        status, headers, body = self.request(web, '/', [wrong])
        self.assertEqual(status, 401)
        self.assertTrue(headers['Content-Type'].startswith('text/html'))
        self.assertIn(b'<form', body)
        self.assert_no_challenge_or_private_echo(headers, body)
        body = self.form()
        status, headers, _ = self.post(web, body, self.post_headers(web, body) + [('Authorization', wrong)])
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/')
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        body = self.form(b'wrong-password-despite-valid-cookie')
        status, headers, _ = self.post(web, body, self.post_headers(web, body) + [('Cookie', cookie)])
        self.assertEqual(status, 401)
        self.assertNotIn('Set-Cookie', headers)

    def test_exact_single_matching_origin_is_required_for_post(self):
        web = self.start_http()
        body = self.form()
        headers = [(key, value) for key, value in self.post_headers(web, body) if key != 'Origin']
        for origins in ([], ['https://other.invalid'], ['null'], [web.public_origin + '.evil.invalid'],
                        [web.public_origin, web.public_origin], [web.public_origin, 'https://other.invalid']):
            with self.subTest(origins=origins), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                status, response_headers, _ = self.post(web, body, headers + [('Origin', origin) for origin in origins])
                self.assertEqual(status, 403)
                self.assertNotIn('Set-Cookie', response_headers)
                verifier.assert_not_called()

    def test_post_host_fetch_and_duplicate_fetch_guards_run_before_password_verification(self):
        web = self.start_http()
        body = self.form()
        headers = self.post_headers(web, body)
        bad_headers = [[('Host', 'other.invalid')], [('Sec-Fetch-Site', 'cross-site')],
                       [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'), ('Sec-Fetch-Dest', 'document')]]
        for name, value in (('Sec-Fetch-Site', 'same-origin'), ('Sec-Fetch-Mode', 'navigate'), ('Sec-Fetch-Dest', 'document')):
            bad_headers.append([(name, value), (name, value)])
        for extra in bad_headers:
            with self.subTest(extra=extra), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                self.assertEqual(self.post(web, body, headers + extra)[0], 403)
                verifier.assert_not_called()
        self.assertEqual(self.post(web, body, headers, host='other.invalid')[0], 403)

    def test_content_type_is_one_exact_form_type(self):
        web = self.start_http()
        body = self.form()
        headers = [(key, value) for key, value in self.post_headers(web, body) if key != 'Content-Type']
        for values in ([], ['text/plain'], ['application/json'], ['application/x-www-form-urlencoded; charset=utf-8'],
                       ['application/x-www-form-urlencoded', 'application/x-www-form-urlencoded']):
            with self.subTest(values=values), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                status, _, _ = self.post(web, body, headers + [('Content-Type', value) for value in values])
                self.assertEqual(status, 415)
                verifier.assert_not_called()

    def test_content_length_missing_duplicate_invalid_zero_and_oversize(self):
        web = self.start_http()
        body = self.form()
        headers = [(key, value) for key, value in self.post_headers(web, body) if key != 'Content-Length']
        for values, expected in (([], 400), ([str(len(body)), str(len(body))], 400), (['0'], 400),
                                 (['-1'], 400), (['+1'], 400), (['1.0'], 400), (['bad'], 400), (['4097'], 413)):
            with self.subTest(values=values), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                status, _, _ = self.post(web, body, headers + [('Content-Length', value) for value in values])
                self.assertEqual(status, expected)
                verifier.assert_not_called()
        self.assertEqual(self.post(web, body, headers + [('Content-Length', str(len(body) + 1))], end_input=True)[0], 400)

    def test_transfer_and_content_encoding_are_rejected(self):
        web = self.start_http()
        body = self.form()
        for extra in ([('Transfer-Encoding', 'chunked')], [('Transfer-Encoding', 'identity')],
                      [('Content-Encoding', 'gzip')], [('Content-Encoding', 'identity')]):
            with self.subTest(extra=extra), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                status, _, _ = self.post(web, body, self.post_headers(web, body) + extra)
                self.assertIn(status, (400, 415))
                verifier.assert_not_called()

    def test_form_parser_rejects_extra_duplicate_missing_and_malformed_fields(self):
        web = self.start_http()
        for body in (b'password=', b'password', b'username=fixture', b'password=x&password=x',
                     b'password=x&other=y', b'password=%', b'password=%ZZ', b'password=%FF', b'password=\xff'):
            with self.subTest(body=body), mock.patch.object(self.auth, 'verify', wraps=self.auth.verify) as verifier:
                status, headers, _ = self.post(web, body)
                self.assertEqual(status, 400)
                self.assertNotIn('Set-Cookie', headers)
                verifier.assert_not_called()

    def test_password_length_is_measured_in_utf8_bytes(self):
        web = self.start_http()
        for password, expected in (('x', 401), ('é' * 256, 401), ('é' * 257, None)):
            with self.subTest(byte_length=len(password.encode())), mock.patch.object(self.auth, 'verify', return_value=False) as verifier:
                status, _, _ = self.post(web, urlencode({'password': password}).encode())
                if expected:
                    self.assertEqual(status, expected)
                    verifier.assert_called_once_with(self.user, password.encode())
                else:
                    self.assertIn(status, (400, 413))
                    verifier.assert_not_called()

    def test_all_non_login_mutations_and_legacy_login_remain_disabled(self):
        web = self.start_http()
        for path, method in (('/', 'POST'), ('/api/refresh', 'POST'), ('/login?x=1', 'POST'),
                             ('/login', 'PUT'), ('/login', 'PATCH'), ('/login', 'DELETE'), ('/login', 'OPTIONS')):
            with self.subTest(path=path, method=method):
                self.assertEqual(self.post(web, path=path, method=method)[0], 405)
        for auth, origin in ((self.auth, None), ((self.user, hashlib.sha256(self.password).digest()), web.public_origin),
                             (None, web.public_origin)):
            web.auth, web.public_origin = auth, origin
            self.assertEqual(self.post(web, headers=[('Content-Length', '0')])[0], 405)
        web.snapshot_cache.get.assert_not_called()

    def test_form_and_basic_share_failure_gate_but_existing_cookie_bypasses_it(self):
        web = self.start_http()
        cookie = self.auth.cookie().split(';', 1)[0]
        wrong_header = 'Basic ' + base64.b64encode(self.user + b':wrong-fixture').decode()
        real_kdf = server.hashlib.pbkdf2_hmac
        with mock.patch.object(server.time, 'monotonic', return_value=100.0), \
             mock.patch.object(server.hashlib, 'pbkdf2_hmac', wraps=real_kdf) as kdf:
            for _ in range(5):
                self.assertEqual(self.post(web, self.form(b'wrong-form-fixture'))[0], 401)
                self.assertEqual(self.request(web, '/api/snapshot', [wrong_header])[0], 401)
            self.assertEqual(kdf.call_count, 10)
            self.assertEqual(self.post(web)[0], 401)
            self.assertEqual(kdf.call_count, 10)
            self.assertEqual(self.request(web, '/api/snapshot', headers=[('Cookie', cookie)])[0], 200)
            self.assertEqual(kdf.call_count, 10)


if __name__ == '__main__':
    unittest.main()
