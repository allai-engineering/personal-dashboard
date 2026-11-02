"""Manual read-only capture into private staging files; never called by HTTP or cron."""
import argparse
import concurrent.futures
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'release'))
import cockpit
import server


def private_json(path):
    mode = path.lstat()
    if not stat.S_ISREG(mode.st_mode) or mode.st_uid != os.getuid() or mode.st_mode & 0o077:
        raise ValueError('private_file_required')
    return json.loads(server.read_regular(path, 16384), parse_constant=server.reject_json_constant)


def publish(directory, name, value):
    body = json.dumps(value, ensure_ascii=True, allow_nan=False).encode()
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.capture-', delete=False) as output:
        temp = Path(output.name)
        os.fchmod(output.fileno(), 0o600)
        output.write(body); output.flush(); os.fsync(output.fileno())
    try:
        os.replace(temp, directory / name)
    finally:
        temp.unlink(missing_ok=True)


def remote(source, kind, root, sudo=False):
    alias = source['alias']
    if not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,80}', alias):
        raise ValueError('invalid_source_alias')
    if not isinstance(root, str) or not root.startswith('/') or any(ord(c) < 32 for c in root):
        raise ValueError('invalid_source_path')
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-T']
    if source.get('ssh_config'):
        cmd += ['-F', str(Path(source['ssh_config']).expanduser())]
    code = (Path(__file__).resolve().parents[1] / 'release/cockpit_read.py').read_bytes()
    if kind == 'verifier':
        # Copy only the existing password verifier through a private encrypted pipe;
        # the production session-signing key is never transferred.
        code = b'import json,sys\nv=json.load(open(sys.argv[1]))\nsys.stdout.write(json.dumps({k:v[k] for k in ("username","password_pbkdf2_sha256","salt")}))\n'
        args = [root]
    else:
        args = [kind, root]
    command = ('sudo -n ' if sudo else '') + 'python3 -I -B - ' + ' '.join(shlex.quote(a) for a in args)
    result = subprocess.run(cmd + [alias, command], input=code, capture_output=True, timeout=45)
    if result.returncode or len(result.stdout) > 16 * 1024 * 1024:
        raise ValueError('source_read_failed')
    return json.loads(result.stdout, parse_constant=server.reject_json_constant,
                      parse_float=server.finite_json_float)


def capture(config, directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    meta = directory.lstat()
    repo = Path(__file__).resolve().parents[1]
    if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077
            or directory.resolve().is_relative_to(repo)
            or any((parent / '.git').exists() for parent in (directory.resolve(), *directory.resolve().parents))):
        raise ValueError('private_external_directory_required')
    fd = os.open(directory / 'capture.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        lock_meta = os.fstat(lock.fileno())
        if not stat.S_ISREG(lock_meta.st_mode) or lock_meta.st_uid != os.getuid() or lock_meta.st_mode & 0o077:
            raise ValueError('private_lock_required')
        fcntl.flock(lock, fcntl.LOCK_EX)
        dashboard, court = config['dashboard'], config['court']
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            work = {'dashboard': pool.submit(remote, dashboard, 'dashboard', dashboard['data_root'], True),
                    'hermes': pool.submit(remote, dashboard, 'hermes', config['hermes_home'], True),
                    'court': pool.submit(remote, court, 'court', court['data_root'])}
            results = {}
            for key, future in work.items():
                try:
                    results[key] = future.result()
                except (OSError, ValueError, subprocess.SubprocessError, KeyError, TypeError, RecursionError):
                    results[key] = None
        data = results['dashboard']
        if not isinstance(data, dict) or not isinstance(data.get('snapshot.json'), dict):
            raise ValueError('dashboard_snapshot_unavailable')
        snap = data['snapshot.json']
        if snap.get('read_only') is not True or snap.get('schema') != 'cpa-account-dashboard-v1' or snap.get('generation_requests_sent') != 0:
            raise ValueError('invalid_dashboard_source')
        for name in ('snapshot.json', 'operations.json', 'integrations.json', 'external-accounts.json'):
            if data.get(name) is not None:
                publish(directory, name, data[name])
        h = results['hermes'] or {'tasks': [], 'profiles': [{'id': p, 'status': 'unavailable', 'stored_jobs': None} for p in cockpit.PROFILES]}
        c = results['court'] or {'status': 'unavailable', 'observed_at': None, 'receipt_status': 'unavailable',
            'receipt_scope': 'unknown', 'receipt_observed_at': None, 'changes': None, 'important': None,
            'unverified': None, 'carried_forward': None, 'search_status': 'unknown', 'confirmed_dates_available': False, 'known_cases': None}
        value = cockpit.validate({'schema': cockpit.SCHEMA, 'collected_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'read_only': True, 'court': c, 'tasks': h['tasks'], 'profiles': h['profiles'], 'events': []})
        publish(directory, 'cockpit.json', value)
        auth_path = directory / 'staging-auth.json'
        if not auth_path.exists():
            verifier = remote(dashboard, 'verifier', dashboard['auth_path'], True)
            verifier['session_key'] = secrets.token_hex(32)
            publish(directory, 'staging-auth.json', verifier)
        return {'captured': True, 'court_status': c['status'], 'task_records': len(h['tasks']),
                'profile_records': len(h['profiles']), 'production_writes': 0, 'generation_requests': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--private-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(capture(private_json(args.config), args.private_dir)))
    except Exception:
        # Neither SSH diagnostics nor source bodies/verifiers belong in logs.
        print(json.dumps({'captured': False, 'error': 'private_capture_failed'}))
        raise SystemExit(1)
