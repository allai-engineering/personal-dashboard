"""The privileged release boundary is tested offline, without production files or GitHub."""
import io,tarfile,tempfile,pathlib,json,unittest,types
from unittest.mock import patch
from deployment import ui_release as m

def archive(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for name,value in files.items():
   i=tarfile.TarInfo('fixture/'+name);i.size=len(value);tar.addfile(i,io.BytesIO(value))
 return b.getvalue()

class UIReleaseTests(unittest.TestCase):
 def test_paths_and_protected_data_login(self):
  for name in ['web/index.html','web/new-page.mjs','web/assets/chart.png']:self.assertEqual(m.validate_web(name),name)
  for name in ['../x','/web/index.html','web/../server.py','web/.hidden.css','web/login.html','web/limits.mjs','web/model.mjs','server.py','web/assets/malware.py','web/assets/page.svg']:
   with self.subTest(name=name),self.assertRaises(ValueError):m.validate_web(name)
 def test_archive_protects_backend_tests_workflow_and_semantics(self):
  locked={'release/server.py':b'backend','release/web/limits.mjs':b'model','.github/workflows/ci.yml':b'workflow','test_view.mjs':b'tests'}
  policy={'trusted_hashes':{n:m.digest(b) for n,b in locked.items()}}
  assets=m.unpack(archive({**locked,'release/web/index.html':b'new ui'}),policy)
  self.assertEqual(assets,{'web/index.html':b'new ui'})
  for key in locked:
   with self.subTest(key=key),self.assertRaises(ValueError):m.unpack(archive({**locked,key:b'changed','release/web/index.html':b'ui'}),policy)
 def test_new_executable_cannot_change_the_ci_environment(self):
  files={'release/web/index.html':b'ui','sitecustomize.py':b'bad startup code'}
  with self.assertRaisesRegex(ValueError,'unexpected_source_file'):m.unpack(archive(files),{'trusted_hashes':{}})
 def test_archive_rejects_links_and_traversal(self):
  b=io.BytesIO()
  with tarfile.open(fileobj=b,mode='w:gz') as t:
   i=tarfile.TarInfo('fixture/release/web/link.js');i.type=tarfile.SYMTYPE;i.linkname='/etc/shadow';t.addfile(i)
  with self.assertRaises(ValueError):m.unpack(b.getvalue(),{'trusted_hashes':{}})
  with self.assertRaises(ValueError):m.unpack(archive({'../release/web/index.html':b'x'}),{'trusted_hashes':{}})
 def test_apply_clone_permissions_pruning_and_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d).resolve();old=root/'releases/old';old.mkdir(parents=True);(old/'web').mkdir();(old/'server.py').write_bytes(b'backend');(old/'web/index.html').write_bytes(b'old');(old/'web/unused.js').write_bytes(b'old')
   current=root/'current';current.symlink_to(old);state=root/'state';state.mkdir()
   policy={'trusted_hashes':{'release/server.py':m.digest(b'backend')},'runtime_files':[]}
   assets={'web/index.html':b'new'}
   with patch.object(m,'CURRENT',current),patch.object(m,'ROOT',state),patch.object(m,'candidate',return_value=(assets,123)),patch.object(m,'session',return_value='fixture'),patch.object(m,'health'),patch.object(m,'protected',return_value={'guard':True}),patch.object(m,'restart'),patch.object(m.os,'chown') as chown,patch.object(m.os,'fchown'),patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)):
    receipt=m.apply({'sha':'a'*40,'expected_current':str(old),'review':'Desktop/mobile synthetic screenshots reviewed.'},policy)
    self.assertEqual((current/'web/index.html').read_bytes(),b'new');self.assertFalse((current/'web/unused.js').exists());self.assertTrue(chown.called)
    m.rollback({'expected_current':receipt['release']},policy)
    self.assertEqual(current.resolve(),old);self.assertEqual((current/'web/index.html').read_bytes(),b'old')
 def test_failed_health_returns_to_original_release(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d).resolve();old=root/'old';new=root/'new';old.mkdir();new.mkdir();cur=root/'current';cur.symlink_to(old)
   with patch.object(m,'CURRENT',cur),patch.object(m,'restart') as restart,patch.object(m,'health',side_effect=[ValueError('bad_candidate'),None]):
    with self.assertRaises(ValueError):m.activate(old,new,'fixture',{},None,lambda:None)
    self.assertEqual(cur.resolve(),old);self.assertEqual(restart.call_count,2)
 def test_apply_rejects_missing_visual_review_stale_and_bad_commit(self):
  for value in ['main','b'*39,'../head',None]:
   with self.assertRaises(ValueError):m.candidate(value,{})
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d).resolve();old=root/'old';old.mkdir();cur=root/'current';cur.symlink_to(old)
   with patch.object(m,'CURRENT',cur):
    with self.assertRaisesRegex(ValueError,'stale_current'):m.apply({'sha':'a'*40,'expected_current':'wrong','review':'review'}, {})
    with self.assertRaisesRegex(ValueError,'visual_review_required'):m.apply({'sha':'a'*40,'expected_current':str(old),'review':''}, {})
if __name__=='__main__':unittest.main()
