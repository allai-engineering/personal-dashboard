import pathlib,subprocess,sys,tempfile,unittest

class PublisherLaunch(unittest.TestCase):
 def test_switch_between_resolution_and_exec_keeps_original_script_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp).resolve();old=root/'old';new=root/'new';old.mkdir();new.mkdir()
   for p in (old,new):(p/'cockpit_publish.py').write_text('from pathlib import Path;print(Path(__file__).parent.name)')
   link=root/'current';link.symlink_to(old)
   code='''from pathlib import Path
import os
from deployment import cockpit_launch as m
m.CURRENT=Path(%r)
execute=os.execv
def switch_then_exec(binary,args):
 m.CURRENT.unlink();m.CURRENT.symlink_to(Path(%r));execute(binary,args)
m.os.execv=switch_then_exec
m.main()
'''%(str(link),str(new))
   r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=10)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'old');self.assertEqual(link.resolve(),new)

if __name__=='__main__':unittest.main()
