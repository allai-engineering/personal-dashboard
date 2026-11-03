"""Scheduled publication contract: cadence, source failure and observation provenance."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
import concurrent.futures
import threading
from unittest.mock import patch

from test_cockpit import fixture
import cockpit_publish


class CockpitPublisherTests(unittest.TestCase):
    def setUp(self):
        guard=patch.object(cockpit_publish,'RELEASE_LINK',cockpit_publish.RELEASE_DIRECTORY)
        guard.start();self.addCleanup(guard.stop)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        gate=Path(temp.name)/'release.lock';gate.touch()
        mock=patch.object(cockpit_publish,'RELEASE_GATE',gate);mock.start();self.addCleanup(mock.stop)
    def test_local_tick_observes_completed_run_without_another_external_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);now=dt.datetime.now(dt.timezone.utc);config={'hermes_home':str(root/'hermes')}
            before=fixture(now);(root/'cockpit.json').write_text(json.dumps(before))
            (root/'cockpit-cadence.json').write_text(json.dumps({'last_attempt':now.timestamp()}))
            local={'tasks':[], 'profiles':before['profiles'], 'work':{'status':'ok','observed_at':now.isoformat(),'items':[]}}
            def external(_):raise AssertionError('local status tick must not read external sources')
            with patch.object(cockpit_publish,'RELEASE_LINK',cockpit_publish.RELEASE_DIRECTORY),patch.object(cockpit_publish.reader,'hermes',return_value=local) as read:
                result=cockpit_publish.publish(root,config,now=now+dt.timedelta(seconds=30),court_read=external)
            self.assertEqual(result['status'],'local_published');read.assert_called_once()
            after=json.loads((root/'cockpit.json').read_text())
            self.assertEqual(after['court'],before['court']);self.assertEqual(after['events'],before['events'])
            self.assertEqual(after['collected_at'],(now+dt.timedelta(seconds=30)).isoformat())
    def test_inactive_release_cannot_write_or_read_external_when_due(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(cockpit_publish,'RELEASE_LINK',root/'inactive'):
                result=cockpit_publish.publish(root,{},court_read=lambda _:self.fail('inactive external read'))
            self.assertEqual(result['status'],'stale_release')
            self.assertFalse((root/'cockpit-cadence.json').exists());self.assertFalse((root/'cockpit.json').exists())
    def test_switch_during_external_read_cannot_replace_current_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);now=dt.datetime.now(dt.timezone.utc);before=fixture(now)
            path=root/'cockpit.json';path.write_text(json.dumps(before));link=root/'current';link.symlink_to(cockpit_publish.RELEASE_DIRECTORY)
            def external(_):
                link.unlink();link.symlink_to(root/'new-release');return before['court']
            with patch.object(cockpit_publish,'RELEASE_LINK',link):
                result=cockpit_publish.publish(root,{'hermes_home':str(root/'hermes')},now=now,court_read=external)
            self.assertEqual(result['status'],'stale_release');self.assertEqual(json.loads(path.read_text()),before)
    def test_release_switch_waits_for_atomic_snapshot_commit(self):
        from deployment import ui_release
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();link=root/'current';link.symlink_to(cockpit_publish.RELEASE_DIRECTORY)
            entered=threading.Event();switch_entered=threading.Event();finish=threading.Event();atomic=cockpit_publish.atomic
            def switching_release():
                switch_entered.set();ui_release.switch(root/'new')
            def blocked(*args):
                entered.set();self.assertTrue(finish.wait(3));return atomic(*args)
            with patch.object(cockpit_publish,'RELEASE_LINK',link),patch.object(ui_release,'CURRENT',link),patch.object(ui_release,'RELEASE_GATE',cockpit_publish.RELEASE_GATE),patch.object(cockpit_publish,'atomic',side_effect=blocked),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                committing=pool.submit(cockpit_publish.commit_snapshot,root/'cockpit.json',{'synthetic':True})
                self.assertTrue(entered.wait(2));switching=pool.submit(switching_release)
                self.assertTrue(switch_entered.wait(2))
                with self.assertRaises(concurrent.futures.TimeoutError):switching.result(timeout=0.1)
                self.assertEqual(link.resolve(),cockpit_publish.RELEASE_DIRECTORY)
                finish.set();self.assertTrue(committing.result(timeout=3));switching.result(timeout=3)
            self.assertEqual(link.resolve(),root/'new');self.assertEqual(json.loads((root/'cockpit.json').read_text()),{'synthetic':True})
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
            self.assertEqual(cockpit_publish.publish(root, config, now=now+dt.timedelta(minutes=5), court_read=reader)['status'], 'local_published')
            self.assertEqual(json.loads((root/'cockpit.json').read_text())['court'],saved['court'])
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
            self.assertEqual(cockpit_publish.publish(root, config, now=now+dt.timedelta(minutes=5), court_read=unavailable)['status'], 'local_published')

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
