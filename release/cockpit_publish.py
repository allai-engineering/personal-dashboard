"""Read existing Court/Hermes evidence at the existing 15-minute cadence; no agent calls."""
import datetime as dt
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile


def sibling(name):
    spec = importlib.util.spec_from_file_location('publisher_' + name, Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader, schema = sibling('cockpit_read'), sibling('cockpit')


def atomic(path, value, mode=0o600):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        os.fchmod(stream.fileno(), mode)
        if mode == 0o640:
            os.fchown(stream.fileno(), -1, path.parent.stat().st_gid)
        stream.write(json.dumps(value, allow_nan=False).encode())
        stream.flush();os.fsync(stream.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def fetch_court(config):
    alias, root = config['court_alias'], config['court_root']
    if not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,80}', alias):
        raise ValueError('court_alias')
    if not isinstance(root, str) or not root.startswith('/') or any(ord(c) < 32 for c in root):
        raise ValueError('court_root')
    result = subprocess.run(['/usr/sbin/runuser', '-u', 'hermes', '--', '/usr/bin/ssh',
        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
        '-T', alias, 'python3 -I -B - court ' + shlex.quote(root)],
        input=Path(reader.__file__).read_bytes(), capture_output=True, timeout=30)
    if result.returncode or len(result.stdout) > 524288:
        raise ValueError('court_unavailable')
    return json.loads(result.stdout)


def publish(directory, config, now=None, court_read=fetch_court):
    now = now or dt.datetime.now(dt.timezone.utc)
    fd = os.open(directory / 'cockpit-publish.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = directory / 'cockpit-cadence.json'
        state = reader.read(state_path) or {}
        last = state.get('last_attempt')
        if type(last) in (int, float) and now.timestamp() - last < 900:
            return {'status': 'not_due'}
        atomic(state_path, {'last_attempt': now.timestamp()})
        try:
            court = court_read(config)
        except (OSError, ValueError, subprocess.SubprocessError):
            court = {'status': 'unavailable', 'observed_at': None, 'receipt_status': 'unavailable',
                'receipt_scope': 'unknown', 'receipt_observed_at': None, 'changes': None, 'important': None,
                'unverified': None, 'carried_forward': None, 'search_status': 'unknown',
                'confirmed_dates_available': False, 'known_cases': None}
        hermes = reader.hermes(Path(config['hermes_home']))
        value = schema.validate({'schema': schema.SCHEMA, 'collected_at': now.isoformat(), 'read_only': True,
            'court': court, 'tasks': hermes['tasks'], 'profiles': hermes['profiles'], 'events': []}, now=now)
        atomic(directory / 'cockpit.json', value, 0o640)
        return {'status': 'partial' if court['status'] == 'unavailable' else 'published'}


if __name__ == '__main__':
    try:
        config_path = Path('/etc/cpa-dashboard/cockpit-sources.json')
        meta = config_path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or meta.st_mode & 0o077:
            raise ValueError('private_source_config_required')
        config = reader.read(config_path, 16384)
        if not isinstance(config, dict) or set(config) != {'hermes_home', 'court_alias', 'court_root'}:
            raise ValueError('source_config')
        if not isinstance(config['hermes_home'], str) or not config['hermes_home'].startswith('/'):
            raise ValueError('hermes_home')
        print(json.dumps(publish(Path('/var/lib/cpa-dashboard'), config)))
    except Exception:
        print(json.dumps({'status': 'collection_failed'}))
        raise SystemExit(1)
