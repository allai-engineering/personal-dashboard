"""Scheduled publication contract: cadence, source failure and observation provenance."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from test_cockpit import fixture
import cockpit_publish


class CockpitPublisherTests(unittest.TestCase):
    def test_existing_tick_publishes_once_per_fifteen_minutes_and_preserves_source_time(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now = dt.datetime.now(dt.timezone.utc)
            observed = now - dt.timedelta(hours=6)
            court = fixture(observed)['court']
            calls = []
            config = {'hermes_home': str(root / 'hermes'), 'court_root': '/synthetic/court', 'court_alias': 'court'}
            def reader(_):
                calls.append(True)
                return court
            result = cockpit_publish.publish(root, config, now=now, court_read=reader)
            self.assertEqual(result['status'], 'published')
            saved = json.loads((root / 'cockpit.json').read_text())
            self.assertEqual(saved['court']['observed_at'], observed.isoformat())
            self.assertTrue(saved['read_only'])
            before = (root / 'cockpit.json').read_bytes()
            self.assertEqual(cockpit_publish.publish(root, config, now=now+dt.timedelta(minutes=5), court_read=reader)['status'], 'not_due')
            self.assertEqual((root / 'cockpit.json').read_bytes(), before)
            self.assertEqual(len(calls), 1)
            self.assertEqual(cockpit_publish.publish(root, config, now=now+dt.timedelta(minutes=15), court_read=reader)['status'], 'published')
            self.assertEqual(len(calls), 2)

    def test_failed_read_publishes_unknown_without_old_success_and_throttles_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);now = dt.datetime.now(dt.timezone.utc)
            config = {'hermes_home': str(root / 'hermes'), 'court_root': '/synthetic/court', 'court_alias': 'court'}
            def unavailable(_):
                raise OSError('PRIVATE_TRANSPORT_ERROR')
            result = cockpit_publish.publish(root, config, now=now, court_read=unavailable)
            saved = json.loads((root / 'cockpit.json').read_text())
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(saved['court']['status'], 'unavailable')
            self.assertIsNone(saved['court']['changes'])
            self.assertIsNone(saved['court']['observed_at'])
            self.assertNotIn('PRIVATE', json.dumps(saved))
            self.assertEqual(cockpit_publish.publish(root, config, now=now+dt.timedelta(minutes=5), court_read=unavailable)['status'], 'not_due')

    def test_malformed_source_cannot_retain_a_recent_successful_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);now=dt.datetime.now(dt.timezone.utc)
            previous=fixture(now-dt.timedelta(minutes=16));previous['court']['receipt_status']='ok'
            (root/'cockpit.json').write_text(json.dumps(previous))
            config={'hermes_home':str(root/'hermes'),'court_root':'/synthetic/court','court_alias':'court'}
            result=cockpit_publish.publish(root,config,now=now,court_read=lambda _: {})
            saved=json.loads((root/'cockpit.json').read_text())
            self.assertEqual(result['status'],'partial')
            self.assertEqual(saved['court']['receipt_status'],'unavailable')
            self.assertIsNone(saved['court']['changes'])


if __name__ == '__main__':
    unittest.main()
