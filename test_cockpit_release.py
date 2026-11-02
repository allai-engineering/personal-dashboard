"""The owner integration transaction restores core, config and policy on failed health."""
from pathlib import Path
import json
import tempfile
import types
import unittest
from unittest.mock import patch

from deployment import cockpit_release as m


class CockpitReleaseTests(unittest.TestCase):
    def exercise_failed_activation(self,shutdown_error=False):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();releases=root/'releases';old=releases/'old';old.mkdir(parents=True)
            (old/'web').mkdir();(old/'server.py').write_bytes(b'old server')
            (old/'web/index.html').write_bytes(b'old ui')
            for name in m.ui.PROTECTED_WEB:(old/'web'/name).write_bytes(b'protected')
            current=root/'current';current.symlink_to(old)
            policy_path=root/'policy.json';policy_path.write_text('{"trusted_hashes":{},"runtime_files":[]}')
            paths={key:root/(key+'.conf') for key in m.FILES}
            original_unit=root/'cpa-dashboard.service';original_unit.write_bytes(b'old dashboard unit')
            paths['latest'].write_bytes(b'old receipt')
            data=root/'data';data.mkdir();(data/'cockpit.json').write_bytes(b'old sidecar')
            files={'release/server.py':b'new server','release/cockpit.py':b'new schema','release/web/index.html':b'new ui'}
            files.update({'release/'+n:b'synthetic source' for n in ('operations.py','integrations.py','cockpit_read.py','cockpit_publish.py')})
            files.update({'release/web/'+n:b'protected' for n in m.ui.PROTECTED_WEB})
            payload={'sha':'a'*40,'expected_current':str(old),'expected_policy_sha256':m.ui.sha(policy_path),
                     'sources':{'hermes_home':'/synthetic/hermes','court_alias':'court','court_root':'/synthetic/court'}}
            def command(args,**kwargs):
                if shutdown_error and args[:2]==['systemctl','disable']:
                    raise ValueError('shutdown_failed')
                if args[:3]==['systemctl','show','cpa-dashboard.service']:
                    return 'argv[]=/usr/bin/python3 -I /opt/cpa-dashboard/current/server.py --port 8766 --snapshot-file /var/lib/cpa-dashboard/snapshot.json --public-origin https://example.test --auth-file /etc/cpa-dashboard/http-auth.json ;'
                return ''
            health=iter([None,ValueError('candidate_health_failed'),None])
            def check(*_):
                result=next(health)
                if result:raise result
            with patch.dict(m.FILES,paths,clear=True),patch.object(m,'DATA',data),patch.object(m,'STATE',root/'backups'),patch.object(m.ui,'CURRENT',current),patch.object(m.ui,'POLICY',policy_path),patch.object(m,'source',return_value=(files,1)),patch.object(m,'guard',return_value={'protected':True}),patch.object(m,'command',side_effect=command),patch.object(m.ui,'verify_current'),patch.object(m.ui,'session',return_value='synthetic-cookie'),patch.object(m.ui,'health',side_effect=check),patch.object(m.ui,'restart'),patch.object(m.os,'chown'),patch.object(m.os,'fchown'),patch.object(m,'verify_sidecar'):
                with self.assertRaisesRegex(ValueError,'rollback_incomplete' if shutdown_error else 'candidate_health_failed'):
                    m.apply(payload)
            self.assertEqual(current.resolve(),old)
            self.assertEqual(original_unit.read_bytes(),b'old dashboard unit')
            self.assertFalse(paths['dashboard'].exists())
            self.assertEqual(paths['latest'].read_bytes(),b'old receipt')
            self.assertFalse(paths['publisher'].exists())
            self.assertFalse(paths['timer'].exists())
            self.assertFalse(paths['sources'].exists())
            self.assertEqual(json.loads(policy_path.read_text()),{'trusted_hashes':{},'runtime_files':[]})
            self.assertEqual((data/'cockpit.json').read_bytes(),b'old sidecar')

    def test_failed_activation_restores_the_previous_core_and_configuration(self):
        self.exercise_failed_activation()

    def test_shutdown_error_does_not_prevent_restoring_core_files_and_policy(self):
        self.exercise_failed_activation(shutdown_error=True)

    def test_new_ui_baseline_keeps_core_tests_and_login_protected(self):
        files={'release/server.py':b'core','release/cockpit_publish.py':b'publisher',
               'release/web/login.html':b'login','test_cockpit_publish.py':b'test',
               'release/web/index.html':b'ui','release/web/cockpit.mjs':b'ui module'}
        policy=m.baseline(files,{'runtime_files':['/synthetic/protected']})
        self.assertIn('release/cockpit_publish.py',policy['trusted_hashes'])
        self.assertIn('test_cockpit_publish.py',policy['trusted_hashes'])
        self.assertIn('release/web/login.html',policy['trusted_hashes'])
        self.assertNotIn('release/web/index.html',policy['trusted_hashes'])
        for name in ('release/cockpit_publish.py','test_cockpit_publish.py','release/web/login.html'):
            changed={**files,name:b'changed'}
            from test_ui_release import archive
            with self.assertRaisesRegex(ValueError,'protected_source_changed'):
                m.ui.unpack(archive(changed),policy)


if __name__=='__main__':unittest.main()
