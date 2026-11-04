"""Loopback-only dashboard; one bounded collection at most once per minute."""
import argparse
import socket
import base64
import binascii
import copy
import datetime as dt
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import importlib.util
import stat
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit

_ops_spec = importlib.util.spec_from_file_location('dashboard_operations', Path(__file__).resolve().with_name('operations.py'))
_ops = importlib.util.module_from_spec(_ops_spec)
_ops_spec.loader.exec_module(_ops)
validate_operations = _ops.validate
_int_spec = importlib.util.spec_from_file_location('dashboard_integrations', Path(__file__).resolve().with_name('integrations.py'))
_int = importlib.util.module_from_spec(_int_spec)
_int_spec.loader.exec_module(_int)
_mail_spec = importlib.util.spec_from_file_location('dashboard_mail', Path(__file__).resolve().with_name('mail_subscriptions.py'))
_mail = importlib.util.module_from_spec(_mail_spec)
_mail_spec.loader.exec_module(_mail)
_secretary_spec = importlib.util.spec_from_file_location('dashboard_secretary', Path(__file__).resolve().with_name('mail_secretary.py'))
_secretary = importlib.util.module_from_spec(_secretary_spec)
_secretary_spec.loader.exec_module(_secretary)

WEB = Path(__file__).resolve().parent / 'web'
ERRORS = {'ssh_timeout', 'ssh_collection_failed', 'snapshot_size_limit', 'invalid_snapshot'}
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
SESSION_SECONDS = 30 * 24 * 60 * 60
SESSION_COOKIE = '__Host-cpa_session'


class PasswordAuth:
    def __init__(self, username, digest, salt, session_key):
        self.username, self.digest, self.salt, self.session_key = username, digest, salt, session_key
        self.lock = threading.Lock()
        self.failures = []

    def verify(self, username, password):
        # One bounded password gate also covers Basic clients; valid cookies skip the KDF.
        with self.lock:
            now = time.monotonic()
            self.failures = [t for t in self.failures if now - t < 60]
            if len(self.failures) >= 10:
                return False
            digest = hashlib.pbkdf2_hmac('sha256', password, self.salt, 600000)
            valid = hmac.compare_digest(username, self.username) & hmac.compare_digest(digest, self.digest)
            if not valid:
                self.failures.append(now)
            return bool(valid)

    def signature(self, token):
        message = b'cpa-session-v1\0' + self.username + b'\0' + self.digest + b'\0' + token.encode('ascii')
        return hmac.new(self.session_key, message, hashlib.sha256).hexdigest()

    def cookie(self):
        token = str(int(time.time()) + SESSION_SECONDS) + '.' + secrets.token_hex(16)
        return (SESSION_COOKIE + '=' + token + '.' + self.signature(token)
                + '; Path=/; Max-Age=' + str(SESSION_SECONDS) + '; Secure; HttpOnly; SameSite=Lax')

    def remembered(self, headers):
        if len(headers) != 1 or len(headers[0]) > 8192:
            return False
        values = [part.strip().partition('=')[2] for part in headers[0].split(';')
                  if part.strip().partition('=')[0] == SESSION_COOKIE]
        if len(values) != 1 or not re.fullmatch(r'[1-9][0-9]{9,11}\.[0-9a-f]{32}\.[0-9a-f]{64}', values[0]):
            return False
        expiry, nonce, signature = values[0].split('.')
        remaining = int(expiry) - int(time.time())
        return 0 < remaining <= SESSION_SECONDS and hmac.compare_digest(signature, self.signature(expiry + '.' + nonce))


class SnapshotCache:
    def __init__(self, collect=None, clock=time.monotonic):
        if collect is None:
            from collector import collect_snapshot
            collect = collect_snapshot
        self.collect, self.clock = collect, clock
        self.condition = threading.Condition()
        self.value = None
        self.loading = False
        self.last_attempt = None
        self.fetched = None
        self.fetched_at = None
        self.error = None

    def view(self):
        age = None if self.fetched is None else max(0, self.clock() - self.fetched)
        last_collection = max((x for x in (self.last_attempt, self.fetched) if x is not None), default=None)
        value = copy.deepcopy(self.value) if self.value is not None else {
            'schema': 'cpa-account-dashboard-v1', 'status': 'unavailable', 'observed_at_utc': None,
            'inventory': {'status': 'unavailable', 'complete': False}, 'accounts': [], 'observed_orphans': []}
        value['cache'] = {'fetched_at_utc': self.fetched_at, 'age_seconds': None if age is None else round(age, 1),
            'stale': age is None or age >= 60 or self.error is not None,
            'refresh_in_progress': self.loading, 'last_error': self.error,
            'refresh_after_seconds': 0 if last_collection is None else max(0, round(60 - (self.clock() - last_collection), 1))}
        return value

    def get(self):
        with self.condition:
            if self.loading:
                if self.value is None:
                    self.condition.wait_for(lambda: not self.loading, timeout=70)
                return self.view()
            if ((self.fetched is not None and self.clock() - self.fetched < 60)
                    or (self.last_attempt is not None and self.clock() - self.last_attempt < 60)):
                return self.view()
            self.loading = True
            self.last_attempt = self.clock()
        try:
            value = self.collect()
            if not isinstance(value, dict) or value.get('schema') != 'cpa-account-dashboard-v1':
                raise RuntimeError('invalid_snapshot')
            with self.condition:
                self.value = value
                self.fetched = self.clock()
                self.fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
                self.error = None
        except Exception as error:
            with self.condition:
                self.error = str(error) if isinstance(error, RuntimeError) and str(error) in ERRORS else 'collection_failed'
        finally:
            with self.condition:
                self.loading = False
                self.condition.notify_all()
        with self.condition:
            return self.view()


def reject_json_constant(_):
    raise ValueError('invalid_snapshot')


def finite_json_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('invalid_snapshot')
    return result


def read_regular(path, limit, root_owned=False):
    # Nonblocking open rejects FIFO/symlink substitutions without hanging a worker.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError('not_regular')
        if root_owned and (metadata.st_uid != 0 or metadata.st_mode & 0o037):
            raise ValueError('insecure_auth_file')
        if metadata.st_size > limit:
            raise OverflowError()
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise OverflowError()
    return raw


def load_auth(path):
    try:
        value = json.loads(read_regular(path, 8192, root_owned=True), parse_constant=reject_json_constant)
        if isinstance(value, dict) and set(value) == {'username', 'password_pbkdf2_sha256', 'salt', 'session_key'}:
            if (not isinstance(value['username'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value['username'])
                    or any(not isinstance(value[key], str) or not re.fullmatch(r'[0-9a-f]{64}', value[key])
                           for key in ('password_pbkdf2_sha256', 'salt', 'session_key'))):
                raise ValueError()
            return PasswordAuth(value['username'].encode('ascii'), bytes.fromhex(value['password_pbkdf2_sha256']),
                                bytes.fromhex(value['salt']), bytes.fromhex(value['session_key']))
        if (not isinstance(value, dict) or set(value) != {'username', 'password_sha256'}
                or not isinstance(value['username'], str)
                or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value['username'])
                or not isinstance(value['password_sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', value['password_sha256'])):
            raise ValueError()
        return value['username'].encode('ascii'), bytes.fromhex(value['password_sha256'])
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        raise ValueError('auth-file must be a root-owned, private regular file with a supported password verifier') from None


def authenticated(headers, auth):
    if auth is None:
        return True
    if len(headers) != 1 or len(headers[0]) > 1024:
        return False
    try:
        scheme, encoded = headers[0].split(' ', 1)
        if scheme.lower() != 'basic':
            return False
        username, password = base64.b64decode(encoded, validate=True).split(b':', 1)
    except (ValueError, binascii.Error):
        return False
    if isinstance(auth, PasswordAuth):
        return auth.verify(username, password)
    # Legacy installer-generated random tokens only; human passwords use PBKDF2 above.
    return hmac.compare_digest(username, auth[0]) & hmac.compare_digest(hashlib.sha256(password).digest(), auth[1])


class SnapshotFile:
    """Read only the publisher's fixed file; HTTP never invokes collection."""
    def __init__(self, path, clock=lambda: dt.datetime.now(dt.timezone.utc), cockpit_path=None):
        self.path, self.clock = Path(path), clock
        self.cockpit_path = Path(cockpit_path) if cockpit_path is not None else None
        self.value = None
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            error = None
            now = self.clock()
            try:
                raw = read_regular(self.path, MAX_SNAPSHOT_BYTES)
                value = json.loads(raw, parse_constant=reject_json_constant, parse_float=finite_json_float)
                if (not isinstance(value, dict) or value.get('schema') != 'cpa-account-dashboard-v1'
                        or value.get('read_only') is not True
                        or type(value.get('generation_requests_sent')) is not int
                        or value['generation_requests_sent'] != 0
                        or value.get('status') not in ('ok', 'partial', 'unavailable')):
                    raise ValueError('invalid_snapshot')
                observed = dt.datetime.fromisoformat(value['observed_at_utc'].replace('Z', '+00:00'))
                if observed.tzinfo is None or observed > now:
                    raise ValueError('invalid_snapshot')
                self.value = copy.deepcopy(value)
            except OSError:
                error = 'file_unavailable'
            except OverflowError:
                error = 'snapshot_size_limit'
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                error = 'invalid_snapshot'
            value = copy.deepcopy(self.value) if self.value is not None else {
                'schema': 'cpa-account-dashboard-v1', 'status': 'unavailable', 'read_only': True,
                'generation_requests_sent': 0, 'observed_at_utc': None,
                'inventory': {'status': 'unavailable', 'complete': False}, 'accounts': [], 'observed_orphans': []}
            observed_text = value['observed_at_utc']
            observed = dt.datetime.fromisoformat(observed_text.replace('Z', '+00:00')) if observed_text else None
            age = (now - observed).total_seconds() if observed else None
            try:
                external=json.loads(read_regular(self.path.parent/'external-accounts.json',1048576),parse_constant=reject_json_constant,parse_float=finite_json_float)
                if (external.get('schema')=='personal-dashboard-sources-v1' and isinstance(external.get('sources'),list)
                        and len(external['sources'])<=10 and all(isinstance(s,dict) and isinstance(s.get('accounts'),list) for s in external['sources'])):
                    value['external']=external
                else:
                    raise ValueError('invalid_external')
            except (OSError,ValueError,OverflowError,TypeError,AttributeError):
                value['external']={'sources':[{'id':'unavailable','title':'Внешние источники','status':'unavailable','accounts':[]}]}
            try:
                operations = json.loads(read_regular(self.path.parent/'operations.json', 1048576),
                                        parse_constant=reject_json_constant, parse_float=finite_json_float)
                value['operations'] = validate_operations(operations)
            except (OSError, ValueError, OverflowError, TypeError, AttributeError, KeyError, RecursionError):
                value['operations'] = None
            try:
                value['integrations'] = _int.validate_integrations(json.loads(read_regular(self.path.parent/'integrations.json',1048576),parse_constant=reject_json_constant,parse_float=finite_json_float))
            except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):
                value['integrations'] = None
            value['cockpit'] = None
            try:
                value['mail_secretary'] = _secretary.validate(json.loads(read_regular(self.path.parent/'mail-secretary.json', 1048576), parse_constant=reject_json_constant, parse_float=finite_json_float))
            except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
                value['mail_secretary'] = None
            try:
                value['mail_subscriptions'] = _mail.validate(json.loads(read_regular(self.path.parent/'mail-subscriptions.json', 1048576), parse_constant=reject_json_constant, parse_float=finite_json_float))
            except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
                value['mail_subscriptions'] = None
            if self.cockpit_path is not None:
                try:
                    spec = importlib.util.spec_from_file_location('dashboard_cockpit', Path(__file__).resolve().with_name('cockpit.py'))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    value['cockpit'] = module.validate(json.loads(read_regular(self.cockpit_path, 524288),
                        parse_constant=reject_json_constant, parse_float=finite_json_float), now=now)
                except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
                    value['cockpit'] = None
            value['cache'] = {'fetched_at_utc': observed_text, 'age_seconds': None if age is None else round(age, 1),
                'stale': error is not None or age is None or age < 0 or age >= 120,
                'refresh_in_progress': False, 'last_error': error,
                'refresh_after_seconds': 0 if age is None else max(0, round(60 - age, 1))}
            return value


def public_origin(value):
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
        if (value != value.strip() or any(ord(char) < 32 for char in value)
                or parsed.scheme != 'https' or not host or len(host) > 253
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment
                or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                       for label in host.split('.'))
                or port is not None and not 1 <= port <= 65535):
            raise ValueError()
        return 'https://' + host + (':' + str(port) if port and port != 443 else '')
    except ValueError:
        raise argparse.ArgumentTypeError('public origin must be an exact HTTPS DNS origin without credentials or a path') from None


def allowed_request(hosts, origins, fetch_site, port, external_origin=None):
    valid_hosts = {host: 'http://' + host for host in ('127.0.0.1:' + str(port), 'localhost:' + str(port))}
    if external_origin:
        valid_hosts[urlsplit(external_origin).netloc] = external_origin
    if len(hosts) != 1 or hosts[0] not in valid_hosts:
        return False
    if len(origins) > 1 or (origins and origins[0] != valid_hosts[hosts[0]]):
        return False
    return fetch_site in (None, 'none', 'same-origin')


def static_file(path, root=WEB):
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return None
    decoded = unquote(parsed.path)
    if '\x00' in decoded or '\\' in decoded or any(part.startswith('.') for part in decoded.split('/') if part):
        return None
    candidate = (root / ('index.html' if decoded == '/' else decoded.lstrip('/'))).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        return None
    return candidate


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass

    def send_body(self, status, body, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin' if getattr(self, 'login_document', False) else 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if status == 401 and not isinstance(getattr(self.server, 'auth', None), PasswordAuth):
            self.send_header('WWW-Authenticate', 'Basic realm="CPA dashboard", charset="UTF-8"')
        if status == 303:
            self.send_header('Location', '/')
        if status in (200, 303) and getattr(self, 'new_session_cookie', None):
            self.send_header('Set-Cookie', self.new_session_cookie)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def origin_allowed(self):
        fetch_site = self.headers.get('Sec-Fetch-Site')
        # A bookmark/external link may open the read-only home page, never a cross-site API fetch.
        if (self.command == 'GET' and self.path == '/' and fetch_site == 'cross-site' and not self.headers.get_all('Origin', [])
                and self.headers.get('Sec-Fetch-Mode') == 'navigate'
                and self.headers.get('Sec-Fetch-Dest') == 'document'):
            fetch_site = 'none'
        if (any(len(self.headers.get_all(name, [])) > 1 for name in ('Sec-Fetch-Site', 'Sec-Fetch-Mode', 'Sec-Fetch-Dest'))
                or not allowed_request(self.headers.get_all('Host', []), self.headers.get_all('Origin', []),
                               fetch_site, self.server.server_port,
                               getattr(self.server, 'public_origin', None))):
            self.send_body(403, b'{"error":"origin_forbidden"}')
            return False
        return True

    def login_page(self, status=200):
        # Native form POST needs its same-origin Origin; no-referrer makes it null.
        self.login_document = True
        body = (WEB / 'login.html').read_bytes()
        error = 'Не удалось войти. Проверьте пароль или повторите через минуту.' if status == 401 else ''
        self.send_body(status, body.replace(b'<!-- error -->', error.encode()), 'text/html; charset=utf-8')

    def do_GET(self):
        self.new_session_cookie = None
        if not self.origin_allowed():
            return
        auth = getattr(self.server, 'auth', None)
        if isinstance(auth, PasswordAuth) and self.path == '/login.css':
            self.send_body(200, (WEB / 'login.css').read_bytes(), 'text/css; charset=utf-8')
            return
        remembered = isinstance(auth, PasswordAuth) and auth.remembered(self.headers.get_all('Cookie', []))
        if not remembered:
            if not authenticated(self.headers.get_all('Authorization', []), auth):
                if isinstance(auth, PasswordAuth) and self.path == '/':
                    self.login_page(401 if self.headers.get_all('Authorization', []) else 200)
                    return
                self.send_body(401, b'{"error":"authentication_required"}')
                return
            if isinstance(auth, PasswordAuth) and getattr(self.server, 'public_origin', None):
                self.new_session_cookie = auth.cookie()
        if self.path in ('/api/snapshot', '/api/refresh'):
            data = self.server.snapshot_cache.get()
            try:
                data['mail_control'] = mail_control({'operation': 'snapshot'})
            except (OSError, ValueError):
                data['mail_control'] = {'available': False, 'decisions': {}}
            self.send_body(200, json.dumps(data, ensure_ascii=False, allow_nan=False).encode())
            return
        target = static_file(self.path)
        if target is None or target.stat().st_size > 16 * 1024 * 1024:
            self.send_body(404, b'{"error":"not_found"}')
            return
        self.send_body(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')

    def do_POST(self):
        self.new_session_cookie = None
        auth = getattr(self.server, 'auth', None)
        if self.path in ('/api/mail-secretary/action', '/api/mail-secretary/evidence'):
            self.mail_post(auth)
            return
        if self.path != '/login' or not isinstance(auth, PasswordAuth) or not getattr(self.server, 'public_origin', None):
            self.read_only()
            return
        if not self.origin_allowed():
            return
        # Login CSRF must fail closed even for clients without Fetch Metadata.
        if len(self.headers.get_all('Origin', [])) != 1:
            self.send_body(403, b'{"error":"origin_forbidden"}')
            return
        lengths = self.headers.get_all('Content-Length', [])
        if (self.headers.get_all('Transfer-Encoding', []) or self.headers.get_all('Content-Encoding', [])
                or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,5}', lengths[0])):
            self.send_body(400, b'{"error":"invalid_login"}')
            return
        length = int(lengths[0])
        if length > 4096:
            self.send_body(413, b'{"error":"login_too_large"}')
            return
        if self.headers.get_all('Content-Type', []) != ['application/x-www-form-urlencoded']:
            self.send_body(415, b'{"error":"unsupported_login_type"}')
            return
        try:
            raw = self.rfile.read(length)
            if not length or len(raw) != length or re.search(rb'%(?![0-9a-fA-F]{2})', raw):
                raise ValueError()
            form = parse_qs(raw.decode('ascii'), keep_blank_values=True, strict_parsing=True,
                            encoding='utf-8', errors='strict', max_num_fields=2)
            if set(form) != {'password'} or len(form['password']) != 1:
                raise ValueError()
            password = form['password'][0].encode('utf-8')
            if not 1 <= len(password) <= 512:
                raise ValueError()
        except (ValueError, UnicodeError, OSError):
            self.send_body(400, b'{"error":"invalid_login"}')
            return
        if not auth.verify(auth.username, password):
            self.login_page(401)
            return
        self.new_session_cookie = auth.cookie()
        self.send_body(303, b'')

    def mail_post(self, auth):
        if not self.origin_allowed():
            return
        if len(self.headers.get_all('Origin', [])) != 1:
            self.send_body(403, b'{"error":"origin_forbidden"}')
            return
        if not isinstance(auth, PasswordAuth) or not auth.remembered(self.headers.get_all('Cookie', [])):
            self.send_body(401, b'{"error":"authentication_required"}')
            return
        lengths = self.headers.get_all('Content-Length', [])
        if (self.headers.get_all('Transfer-Encoding', []) or self.headers.get_all('Content-Encoding', [])
                or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,5}', lengths[0]) or not 1 <= int(lengths[0]) <= 4096):
            self.send_body(400, b'{"error":"invalid_action"}')
            return
        if self.headers.get_all('Content-Type', []) != ['application/json']:
            self.send_body(415, b'{"error":"unsupported_type"}')
            return
        try:
            raw = self.rfile.read(int(lengths[0]))
            value = json.loads(raw, parse_constant=reject_json_constant)
            operation = 'action' if self.path.endswith('/action') else 'evidence'
            if not isinstance(value, dict) or 'operation' in value:
                raise ValueError('invalid_action')
            result = mail_control({**value, 'operation': operation})
            error = result.get('error')
            code = 409 if error in ('decision_conflict', 'request_conflict') else 400 if error in ('unknown_case', 'invalid_reminder', 'invalid_action', 'invalid_id', 'invalid_revision') else 503 if error else 200
            self.send_body(code, json.dumps(result, ensure_ascii=False).encode())
        except (OSError, ValueError, TypeError, RecursionError):
            self.send_body(503, b'{"error":"control_unavailable"}')

    def read_only(self):
        self.send_body(405, b'{"error":"read_only"}')

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = read_only


def mail_control(value):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(30)
        connection.connect('/run/hermes-mail-secretary-control.sock')
        connection.sendall(json.dumps(value, allow_nan=False).encode())
        connection.shutdown(socket.SHUT_WR)
        body = bytearray()
        while len(body) <= 1048576:
            chunk = connection.recv(65536)
            if not chunk:
                break
            body.extend(chunk)
        if len(body) > 1048576:
            raise ValueError('control_response_size')
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError('control_response')
        return result


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, *args, **kwargs):
        self.request_slots = threading.BoundedSemaphore(16)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--snapshot-file', type=Path)
    parser.add_argument('--cockpit-file', type=Path)
    parser.add_argument('--public-origin', type=public_origin)
    parser.add_argument('--auth-file', type=Path)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    if args.snapshot_file is not None and not args.snapshot_file.is_absolute():
        parser.error('snapshot-file must be an absolute path')
    if args.cockpit_file is not None and (not args.cockpit_file.is_absolute() or args.snapshot_file is None):
        parser.error('cockpit-file requires absolute file paths and snapshot-file mode')
    if args.public_origin and args.snapshot_file is None:
        parser.error('public-origin requires snapshot-file mode')
    if args.public_origin and args.auth_file is None:
        parser.error('public-origin requires auth-file')
    try:
        auth = load_auth(args.auth_file) if args.auth_file else None
    except ValueError as error:
        parser.error(str(error))
    server = DashboardServer(('127.0.0.1', args.port), Handler)
    server.snapshot_cache = SnapshotFile(args.snapshot_file, cockpit_path=args.cockpit_file) if args.snapshot_file else SnapshotCache()
    server.public_origin = args.public_origin
    server.auth = auth
    print('CPA dashboard: http://127.0.0.1:' + str(args.port), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
