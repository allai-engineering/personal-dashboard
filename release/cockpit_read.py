"""Fixed read-only source reader. Transport captures its JSON into private files, never logs."""
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

PROFILES = ('default', 'ops', 'dashboard-dev', 'infra-dev', 'lawyer', 'monitor', 'research')


def read_timed(path, limit=4 * 1024 * 1024):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                return None, None
            body = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        if len(body) > limit or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return None, None
        value = json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return value, dt.datetime.fromtimestamp(before.st_mtime, dt.timezone.utc).isoformat()
    except (OSError, ValueError, RecursionError, OverflowError):
        return None, None


def read(path, limit=4 * 1024 * 1024):
    return read_timed(path, limit)[0]


def timestamp(value):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.isoformat() if result.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def count(value):
    if type(value) is int and 0 <= value <= 100000:
        return value
    if isinstance(value, (dict, list)):
        return len(value)
    return None


def court(root):
    base = root / 'evidence/court/kad-akty/_monitoring'
    try:
        today = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()
        days = []
        for p in base.iterdir():
            if not p.is_dir() or p.is_symlink() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', p.name):
                continue
            try:
                if dt.date.fromisoformat(p.name) <= today:
                    days.append(p)
            except ValueError:
                pass
        days.sort()
    except OSError:
        days = []
    day = days[-1] if days else base / 'missing'
    rp, sp = day / 'hermes-run.json', day / 'sostoyanie.json'
    (r, rt), (s, st) = read_timed(rp), read_timed(sp)
    r = r if isinstance(r, dict) else {}
    s = s if isinstance(s, dict) else {}
    receipt_status = r.get('status') if r.get('status') in ('ok', 'partial', 'error') else 'unavailable'
    scope = r.get('scope') if r.get('scope') in ('courts', 'kad', 'kad_metadata') else 'unknown'
    search = s.get('soj_new_case_search')
    search = search if search in ('complete', 'incomplete') else 'unknown'
    missing, carried = count(s.get('ne_provereno')), count(s.get('pereneseno_iz'))
    full = bool(s) and s.get('scope') == 'courts' and scope == 'courts' and receipt_status == 'ok' and missing == 0 and carried == 0 and search == 'complete'
    return {'status': 'ok' if full else 'partial' if r or s else 'unavailable',
            'observed_at': st if s else None, 'receipt_status': receipt_status,
            'receipt_scope': scope, 'receipt_observed_at': rt if r else None,
            'changes': count(r.get('changes')), 'important': count(r.get('important_count')),
            'known_cases': count(s.get('kad')),
            'unverified': missing, 'carried_forward': carried, 'search_status': search,
            'confirmed_dates_available': False}


def liveness(row):
    if row['status'] not in ('running', 'claimed'):
        return 'not_applicable'
    if row['handoff_pending'] or not row['pid'] or row['process_started_at'] is None:
        return 'unverified'
    try:
        # Compare the kernel process incarnation, not just a reusable PID.
        parts = Path('/proc/' + str(int(row['pid'])) + '/stat').read_text().rsplit(')', 1)[1].split()
        if parts[0] == 'Z':
            return 'not_live'
        return 'verified' if int(parts[19]) == int(row['process_started_at']) else 'not_live'
    except FileNotFoundError:
        return 'not_live'
    except (OSError, ValueError, IndexError, TypeError):
        return 'unverified'


def infra_overlay(root,raw,item,contract,now):
    key=hashlib.sha256((raw['record_id']+'\0'+raw['fingerprint']).encode()).hexdigest()
    phase=read(root/'profiles/ops/checkpoints/infra-handoffs'/(key+'.json'),16384)
    if not isinstance(phase,dict):return item
    try:
        if phase.get('schema')!=1 or phase.get('profile')!='infra-dev' or phase.get('record_id')!=raw['record_id'] or phase.get('fingerprint')!=raw['fingerprint'] or phase.get('parent_execution_id')!=raw.get('execution_id'):return item
        if not isinstance(phase.get('native_task_id'),str) or not re.fullmatch(r'sa-\d+-[a-f0-9]{8}',phase['native_task_id']):return item
        if contract.stamp(phase['updated_at'])<contract.stamp(raw['updated_at']):return item
        candidate={**item,**{k:phase[k] for k in ('state','action','blocker','decision','task_ref','updated_at')},'actor':'infra-dev'}
        contract.validate({'status':'ok','observed_at':now,'items':[candidate]})
        return candidate
    except (ValueError,TypeError,KeyError):return item


def incident_work(root, now):
    unavailable={'status':'unavailable','observed_at':now,'items':[]}
    try:
        raw=read(root/'profiles/ops/checkpoints/dashboard-incidents.json',524288)
        if not isinstance(raw,dict) or raw.get('schema')!=1 or not isinstance(raw.get('items'),list) or len(raw['items'])>200:return unavailable
        rows={}
        with closing(sqlite3.connect('file:'+quote(str(root/'profiles/ops/cron/executions.db'),safe='/')+'?mode=ro',uri=True,timeout=3)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            ids=[w.get('execution_id') for w in raw['items'] if isinstance(w,dict) and w.get('execution_id')]
            if ids:rows={r['id']:r for r in db.execute('SELECT id,status,pid,process_started_at,handoff_pending FROM executions WHERE id IN ('+','.join('?' for _ in ids)+')',ids)}
        import importlib.util
        spec=importlib.util.spec_from_file_location('reader_incident_schema',Path(__file__).with_name('incident_schema.py'))
        contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
        items=[]
        for w in raw['items']:
            execution=w.get('execution_id');row=rows.get(execution)
            item={k:v for k,v in w.items() if k not in ('execution_id','subject')}
            item.update(execution_key=hashlib.sha256(('ops:'+execution).encode()).hexdigest()[:24] if execution else None,
                execution_state=row['status'] if row and row['status'] in ('claimed','running','completed','failed') else 'unknown',
                execution_liveness=liveness(row) if row else 'unverified')
            items.append(infra_overlay(root,w,item,contract,now))
        return contract.validate({'status':'ok','observed_at':now,'items':items})
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError,AttributeError,RecursionError):return unavailable


def hermes(root):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    tasks, profiles = [], []
    for profile in PROFILES:
        home = root if profile == 'default' else root / 'profiles' / profile
        job_data = read(home / 'cron/jobs.json') or {}
        jobs = job_data.get('jobs', []) if isinstance(job_data, dict) else []
        jobs = jobs if isinstance(jobs, list) else []
        jobs = {j['id']: j for j in jobs if isinstance(j, dict) and isinstance(j.get('id'), str)}
        rows, status = [], 'empty' if profile=='infra-dev' and isinstance(job_data,dict) and not jobs else 'unavailable'
        path = home / 'cron/executions.db'
        if path.is_file() and not path.is_symlink():
            try:
                with closing(sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro', uri=True, timeout=3)) as db:
                    db.row_factory = sqlite3.Row
                    db.execute('PRAGMA query_only=ON')
                    rows = list(db.execute('SELECT id,job_id,source,status,claimed_at,started_at,finished_at,progress_at,pid,process_started_at,handoff_pending,error IS NOT NULL AS has_error FROM executions ORDER BY julianday(claimed_at) DESC, claimed_at DESC,id DESC LIMIT 1000'))
                status = 'ok' if rows or jobs else 'empty'
            except sqlite3.Error:
                status = 'unavailable'
        chosen, seen = [], set()
        for row in rows:
            key = (row['job_id'], row['source'])
            if key not in seen:
                seen.add(key); chosen.append(row)
        if len(chosen) > 12 or len(jobs) > 12:
            status = 'partial'
        profiles.append({'id': profile, 'status': status, 'stored_jobs': len(jobs) if job_data else None})
        for row in chosen[:12]:
            job = jobs.get(row['job_id'], {})
            label = ' '.join(str(job.get('name') or 'Задание Hermes').split())[:150]
            tasks.append({'id': hashlib.sha256((profile + ':' + str(row['id'])).encode()).hexdigest()[:24],
                'job_key': hashlib.sha256((profile + ':' + str(row['job_id'])).encode()).hexdigest()[:24],
                'profile': profile, 'label': label, 'state': row['status'] if row['status'] in ('claimed', 'running', 'completed', 'failed', 'unknown') else 'unknown',
                'origin': {'builtin': 'scheduled', 'direct': 'manual'}.get(row['source'], 'unknown'),
                **{k: timestamp(row[k]) for k in ('claimed_at', 'started_at', 'finished_at', 'progress_at')},
                'observed_at': now, 'liveness': liveness(row),
                'next_run_at': timestamp(job.get('next_run_at')) if job.get('enabled') is True else None,
                'enabled': job.get('enabled') if type(job.get('enabled')) is bool else None,
                'has_error': bool(row['has_error'])})
        executed = {r['job_id'] for r in chosen}
        for jid, job in list(jobs.items())[:12]:
            if jid in executed or len(tasks) >= 90:
                continue
            tasks.append({'id': hashlib.sha256((profile + ':' + jid).encode()).hexdigest()[:24],
                'job_key': hashlib.sha256((profile + ':' + jid).encode()).hexdigest()[:24],
                'profile': profile, 'label': ' '.join(str(job.get('name') or 'Задание Hermes').split())[:150],
                'state': 'planned' if job.get('enabled') is True else 'paused' if job.get('enabled') is False else 'unknown', 'origin': 'scheduled',
                'claimed_at': None, 'started_at': None, 'finished_at': None, 'progress_at': None,
                'observed_at': now, 'liveness': 'not_applicable',
                'next_run_at': timestamp(job.get('next_run_at')) if job.get('enabled') is True else None,
                'enabled': job.get('enabled') if type(job.get('enabled')) is bool else None, 'has_error': False})
    if len(tasks) > 100:
        for profile in profiles:
            if profile['status'] == 'ok':
                profile['status'] = 'partial'
    return {'tasks': tasks[:100], 'profiles': profiles, 'collected_at': now, 'work':incident_work(root,now)}


def dashboard(root):
    return {name: read(root / name, 8 * 1024 * 1024) for name in
            ('snapshot.json', 'operations.json', 'integrations.json', 'external-accounts.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=('court', 'hermes', 'dashboard'))
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    # stdout is the encrypted SSH data channel, captured privately by the caller.
    print(json.dumps(globals()[args.kind](args.root), ensure_ascii=True, allow_nan=False))
