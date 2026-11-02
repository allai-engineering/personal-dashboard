"""Isolated loopback, file-only working copy under the existing password verifier."""
import argparse
import os
from pathlib import Path
import re

from capture_cockpit import private_json, server


def stage_auth(path):
    value = private_json(path)
    if set(value) != {'username', 'password_pbkdf2_sha256', 'salt', 'session_key'}:
        raise ValueError('invalid_staging_auth')
    if not isinstance(value['username'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value['username']):
        raise ValueError('invalid_staging_auth')
    for key in ('password_pbkdf2_sha256', 'salt', 'session_key'):
        if not isinstance(value[key], str) or not re.fullmatch(r'[0-9a-f]{64}', value[key]):
            raise ValueError('invalid_staging_auth')
    return server.PasswordAuth(value['username'].encode(), bytes.fromhex(value['password_pbkdf2_sha256']),
                               bytes.fromhex(value['salt']), bytes.fromhex(value['session_key']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8891)
    args = parser.parse_args()
    meta = args.private_dir.lstat()
    if args.private_dir.is_symlink() or not args.private_dir.is_dir() or meta.st_uid != os.getuid() or meta.st_mode & 0o077 or not 1024 <= args.port <= 65535:
        parser.error('owner-private staging directory and loopback port required')
    auth = stage_auth(args.private_dir / 'staging-auth.json')
    web = server.DashboardServer(('127.0.0.1', args.port), server.Handler)
    web.auth = auth
    web.public_origin = 'http://127.0.0.1:' + str(args.port)
    web.snapshot_cache = server.SnapshotFile(args.private_dir / 'snapshot.json', cockpit_path=args.private_dir / 'cockpit.json')
    print('Authenticated file-only staging: ' + web.public_origin, flush=True)
    web.serve_forever()
