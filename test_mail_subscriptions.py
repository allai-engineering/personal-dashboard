import copy
import json
import unittest
from mail_subscriptions import validate


def fixture():
    return {'schema': 1, 'checked_at': '2026-11-04T04:00:00+00:00',
            'coverage': [{'mailbox': 'google-test', 'status': 'partial', 'checked_at': '2026-11-04T04:00:00+00:00', 'history_complete': False}],
            'records': [{'id': 'a'*32, 'service': 'example.test', 'amount': '20.00', 'currency': 'USD', 'amount_kind': 'last_payment',
                         'renewal_date': None, 'status': 'observed', 'sources': [{'mailbox': 'google-test', 'ref': 'b'*32,
                         'date': '2026-11-03T04:00:00+00:00', 'fields': ['amount'], 'url': 'https://mail.google.com/mail/?authuser=owner%40example.test#all/abc123'}]}]}


class MailSchemaTests(unittest.TestCase):
    def test_hosted_snapshot_reads_only_validated_mail_sidecar(self):
        import datetime as dt
        from pathlib import Path
        import tempfile
        from server import SnapshotFile
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'snapshot.json'
            p.write_text(json.dumps({'schema':'cpa-account-dashboard-v1','status':'ok','read_only':True,'generation_requests_sent':0,
                                    'observed_at_utc':'2026-11-04T04:00:00+00:00','accounts':[]}))
            sidecar = p.parent/'mail-subscriptions.json'; sidecar.write_text(json.dumps(fixture()))
            cache = SnapshotFile(p, lambda: dt.datetime(2026,11,4,5,tzinfo=dt.timezone.utc))
            self.assertEqual(len(cache.get()['mail_subscriptions']['records']), 1)
            d = fixture(); d['records'][0]['text'] = 'PRIVATE_MAIL_TEXT'
            sidecar.write_text(json.dumps(d)); result = cache.get()
            self.assertIsNone(result['mail_subscriptions'])
            self.assertNotIn('PRIVATE_MAIL_TEXT', json.dumps(result))

    def test_valid_unknown_is_not_zero(self):
        d = fixture(); self.assertEqual(validate(d), d)
        d['records'][0].update(amount=None, currency=None, amount_kind='unknown')
        self.assertIsNone(validate(d)['records'][0]['amount'])

    def test_texts_model_fields_and_arbitrary_links_are_refused(self):
        for field in ('text', 'subject', 'quote', 'token', 'body'):
            d = fixture(); d['records'][0][field] = 'private'
            with self.assertRaises(ValueError): validate(d)
        for url in ('https://evil.test/', 'javascript:alert(1)', 'https://mail.google.com@evil.test/', 'https://mail.google.com/mail/?authuser=x#all/abc123&private'):
            d = fixture(); d['records'][0]['sources'][0]['url'] = url
            with self.assertRaises(ValueError): validate(d)

    def test_duplicate_invalid_numbers_dates_currency(self):
        for changes in ({'amount': 0}, {'amount': 'NaN'}, {'currency': 'XXX'}, {'renewal_date': 'tomorrow'}, {'id': 'private'}):
            d = fixture(); d['records'][0].update(changes)
            with self.assertRaises((ValueError, TypeError)): validate(d)
        d = fixture(); d['records'].append(copy.deepcopy(d['records'][0]))
        with self.assertRaises(ValueError): validate(d)
