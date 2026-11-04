import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from mail_secretary import validate


def fixture():
    return {'schema': 1, 'checked_at': '2026-11-04T10:00:00+00:00', 'run_state': 'partial',
        'stop_reason': 'backlog', 'pending': 3, 'case_counts': {'needs_user': 1, 'waiting': 0, 'done': 0}, 'omitted_cases': 0,
        'coverage': {'ok': 3, 'partial': 1, 'unavailable': 0, 'scope': 'bounded_inbox_and_targeted'},
        'cases': [{'id': 'a' * 32, 'service': 'unknown', 'kind': 'renewal', 'state': 'needs_user',
            'deadline': None, 'confidence': 'supported_notice', 'blocker': 'owner_decision',
            'next_action': 'review_notice', 'owner': 'user', 'observed_at': '2026-11-03T10:00:00+00:00',
            'updated_at': '2026-11-04T10:00:00+00:00', 'last_operation': 'evidence_verified', 'sources': ['b' * 32]}],
        'operations': [{'action': 'read', 'ref': 'b' * 32, 'outcome': 'ok', 'at': '2026-11-04T10:00:00+00:00'}]}


class SecretarySchemaTests(unittest.TestCase):
    def test_substantive_reply_is_reviewable_without_false_completion(self):
        data = fixture(); data['cases'][0]['kind'] = 'reply'
        row = validate(data)['cases'][0]
        self.assertEqual(row['state'], 'needs_user')
        self.assertEqual(row['next_action'], 'review_notice')

    def test_private_fields_and_free_model_strings_rejected(self):
        self.assertIsNone(validate(fixture())['cases'][0]['deadline'])
        for field in ('subject', 'body', 'quote', 'account', 'relations', 'email'):
            data = fixture(); data['cases'][0][field] = 'PRIVATE'
            with self.assertRaises(ValueError): validate(data)
        for field in ('service', 'kind', 'blocker', 'next_action', 'owner'):
            data = fixture(); data['cases'][0][field] = 'private@example.test'
            with self.assertRaises(ValueError): validate(data)

    def test_snapshot_rejects_invalid_sidecar_without_leaking(self):
        from server import SnapshotFile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            path.write_text(json.dumps({'schema': 'cpa-account-dashboard-v1', 'status': 'ok', 'read_only': True,
                'generation_requests_sent': 0, 'observed_at_utc': '2026-11-04T10:00:00+00:00', 'accounts': []}))
            sidecar = path.parent / 'mail-secretary.json'; sidecar.write_text(json.dumps(fixture()))
            cache = SnapshotFile(path, lambda: dt.datetime(2026, 11, 4, 10, tzinfo=dt.timezone.utc))
            self.assertEqual(len(cache.get()['mail_secretary']['cases']), 1)
            data = fixture(); data['cases'][0]['text'] = 'PRIVATE_MAIL_TEXT'
            sidecar.write_text(json.dumps(data)); result = cache.get()
            self.assertIsNone(result['mail_secretary'])
            self.assertNotIn('PRIVATE_MAIL_TEXT', json.dumps(result))
