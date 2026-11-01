import datetime as dt,json,pathlib,tempfile,unittest
from server import SnapshotFile
class ExternalTests(unittest.TestCase):
 def test_external_file_is_read_without_network_and_missing_is_unknown(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'snapshot.json';p.write_text(json.dumps({'schema':'cpa-account-dashboard-v1','read_only':True,'generation_requests_sent':0,'status':'ok','observed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'accounts':[]}))
   reader=SnapshotFile(p)
   self.assertEqual(reader.get()['external']['sources'][0]['status'],'unavailable')
   ext=p.with_name('external-accounts.json');ext.write_text(json.dumps({'schema':'personal-dashboard-sources-v1','sources':[{'id':'main','accounts':[]}]}))
   self.assertEqual(reader.get()['external']['sources'][0]['id'],'main')
   for body in ['not json','{"schema":"wrong","sources":[]}','{"schema":"personal-dashboard-sources-v1","sources":[42]}']:
    ext.write_text(body);self.assertEqual(reader.get()['external']['sources'][0]['status'],'unavailable')
if __name__=='__main__':unittest.main()
