"""Cockpit contract observed through the existing file/snapshot interface."""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import sqlite3
import sys
import unittest

import server
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import cockpit_read
from stage_cockpit import stage_auth


def fixture(now):
    return {'schema': 'captain-cockpit-v1', 'collected_at': now.isoformat(), 'read_only': True,
            'court': {'status': 'partial', 'observed_at': now.isoformat(), 'receipt_status': 'ok',
                      'receipt_scope': 'kad_metadata', 'receipt_observed_at': now.isoformat(),
                      'changes': 0, 'important': 0, 'unverified': 1, 'carried_forward': 2,
                      'search_status': 'incomplete', 'confirmed_dates_available': False, 'known_cases': 26},
            'tasks': [], 'profiles': [{'id': 'lawyer', 'status': 'ok', 'stored_jobs': 1}],
            'events': []}


class CockpitContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = dt.datetime(2026, 11, 2, 12, tzinfo=dt.timezone.utc)
        self.base = Path(self.tmp.name) / 'snapshot.json'
        self.base.write_text(json.dumps({'schema': 'cpa-account-dashboard-v1', 'status': 'ok',
            'read_only': True, 'generation_requests_sent': 0, 'observed_at_utc': self.now.isoformat(),
            'inventory': {'status': 'ok', 'complete': True}, 'accounts': [], 'observed_orphans': []}))
        self.side = self.base.with_name('cockpit.json')

    def test_narrow_success_does_not_clear_broader_partial_coverage(self):
        self.side.write_text(json.dumps(fixture(self.now)))
        cache = server.SnapshotFile(self.base, lambda: self.now, cockpit_path=self.side)
        value = cache.get()['cockpit']
        self.assertEqual(value['court']['receipt_status'], 'ok')
        self.assertEqual(value['court']['status'], 'partial')
        self.assertEqual(value['court']['carried_forward'], 2)
        self.assertFalse(value['court']['confirmed_dates_available'])

    def test_future_sidecar_is_not_fresh_evidence(self):
        value = fixture(self.now + dt.timedelta(hours=1))
        self.side.write_text(json.dumps(value))
        cache = server.SnapshotFile(self.base, lambda: self.now, cockpit_path=self.side)
        self.assertIsNone(cache.get()['cockpit'])

    def test_sidecar_rejects_private_extras_missing_files_and_fake_all_clear(self):
        cache = server.SnapshotFile(self.base, lambda: self.now, cockpit_path=self.side)
        for value in [dict(fixture(self.now), prompt='PRIVATE_BODY'),
                      {**fixture(self.now), 'court': {**fixture(self.now)['court'], 'status': 'ok'}},
                      {**fixture(self.now), 'court': {**fixture(self.now)['court'], 'changes': False}}]:
            with self.subTest(value=value['court']['status']):
                self.side.write_text(json.dumps(value))
                result = cache.get()
                self.assertIsNone(result['cockpit'])
                self.assertNotIn('PRIVATE_BODY', json.dumps(result))
        self.side.write_text('PRIVATE_MALFORMED')
        self.assertIsNone(cache.get()['cockpit'])
        self.side.unlink()
        self.assertIsNone(cache.get()['cockpit'])
        self.side.symlink_to(self.base)
        self.assertIsNone(cache.get()['cockpit'])

    def test_reader_keeps_failed_scheduled_and_manual_success_without_output_text(self):
        root = Path(self.tmp.name) / 'hermes'
        cron = root / 'profiles/lawyer/cron'; cron.mkdir(parents=True)
        (cron / 'jobs.json').write_text(json.dumps({'jobs': [{'id': 'job-1', 'name': 'Synthetic court check',
            'enabled': True, 'prompt': 'PRIVATE_PROMPT', 'next_run_at': '2026-11-04T06:00:00Z'}]}))
        path = cron / 'executions.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE executions(id TEXT,job_id TEXT,source TEXT,status TEXT,claimed_at TEXT,started_at TEXT,finished_at TEXT,progress_at TEXT,pid INTEGER,process_started_at INTEGER,handoff_pending INTEGER,error TEXT)')
            for row in [('scheduled-failure', 'builtin', 'failed', 'PRIVATE_ERROR'), ('manual-success', 'direct', 'completed', None), ('claimed-unverified', 'custom', 'running', None)]:
                db.execute('INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (row[0], 'job-1', row[1], row[2], '2026-11-02T09:00:00+03:00', None, None, None, os.getpid(), None, 0, row[3]))
        before = path.read_bytes()
        result = cockpit_read.hermes(root)
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual({(t['origin'], t['state']) for t in result['tasks']},
                         {('scheduled', 'failed'), ('manual', 'completed'), ('unknown', 'running')})
        self.assertEqual(next(t for t in result['tasks'] if t['state'] == 'running')['liveness'], 'unverified')
        empty = next(p for p in result['profiles'] if p['id'] == 'ops')
        self.assertEqual(empty['status'], 'unavailable')
        self.assertIsNone(empty['stored_jobs'])

    def test_court_reader_separates_receipt_scope_and_carry_forward(self):
        root = Path(self.tmp.name) / 'court'
        base = root / 'evidence/court/kad-akty/_monitoring'
        today = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date().isoformat()
        day = base / today; day.mkdir(parents=True)
        (day / 'hermes-run.json').write_text(json.dumps({'status': 'ok', 'scope': 'kad_metadata',
            'changes': 0, 'important_count': 0, 'errors': ['PRIVATE_ERROR'], 'report_path': 'PRIVATE_PATH'}))
        (day / 'sostoyanie.json').write_text(json.dumps({'scope': 'courts', 'ne_provereno': ['PRIVATE_CASE'],
            'pereneseno_iz': ['a', 'b'], 'soj_new_case_search': 'incomplete'}))
        for suffix in (today + '-local-review', '2999-01-01', '2026-99-99'):
            p = base / suffix; p.mkdir(); (p / 'hermes-run.json').write_text('{"changes":999}')
        result = cockpit_read.court(root)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual((result['changes'], result['unverified'], result['carried_forward']), (0, 1, 2))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertFalse(result['confirmed_dates_available'])
        self.assertIsNone(cockpit_read.court(root / 'missing')['changes'])

    def test_staging_verifier_requires_private_regular_owner_file(self):
        auth = Path(self.tmp.name) / 'staging-auth.json'
        value = {'username': 'fixture', 'password_pbkdf2_sha256': 'a1' * 32,
                 'salt': 'b2' * 32, 'session_key': 'c3' * 32}
        auth.write_text(json.dumps(value)); auth.chmod(0o600)
        self.assertIsInstance(stage_auth(auth), server.PasswordAuth)
        auth.chmod(0o644)
        with self.assertRaises(ValueError):
            stage_auth(auth)

    def test_missing_or_invalid_enabled_is_not_a_paused_schedule(self):
        root = Path(self.tmp.name) / 'hermes'
        cron = root / 'cron'; cron.mkdir(parents=True)
        (cron / 'jobs.json').write_text(json.dumps({'jobs': [
            {'id': 'missing', 'name': 'Synthetic unknown'},
            {'id': 'invalid', 'name': 'Synthetic invalid', 'enabled': 'false'},
            {'id': 'paused', 'name': 'Synthetic paused', 'enabled': False}]}))
        rows = cockpit_read.hermes(root)['tasks']
        self.assertEqual([(t['state'], t['enabled']) for t in rows],
                         [('unknown', None), ('unknown', None), ('paused', False)])


if __name__ == '__main__':
    unittest.main()
