import concurrent.futures,fcntl,threading,copy,datetime as dt,hashlib,importlib.util,json,os,pathlib,sqlite3,subprocess,tempfile,unittest
from unittest.mock import patch
import incident_schema as schema
import cockpit_read,cockpit_publish
from deployment import incident_ops as ops
from test_cockpit import fixture

class Incidents(unittest.TestCase):
 def setUp(self):self.now=dt.datetime.now(dt.timezone.utc)
 def record(self,state='open',condition='service:warning'):
  return {'record_id':'machine-node','condition_key':condition,'source_state':state,'source_at':self.now.isoformat()}
 def state(self):return ops.reconcile({},[self.record()],self.now)
 def payload(self,row,state='waiting',blocker='no_safe_procedure',decision=None):
  return {k:row[k] for k in ['record_id','fingerprint']}|{'state':state,'action':'inspect_service','blocker':blocker,'decision':decision,'task_ref':None}
 def test_same_condition_does_not_requeue_and_recurrence_does(self):
  state=self.state();ops.report(state,self.payload(state['items'][0]),'execution',self.now,schema)
  later=self.now+dt.timedelta(minutes=15)
  again=ops.reconcile(state,[self.record()],later);self.assertEqual(again['items'][0]['state'],'waiting');self.assertEqual(again['items'][0]['updated_at'],self.now.isoformat())
  missing=ops.reconcile(copy.deepcopy(again),[],later);self.assertEqual(missing['items'][0]['source_state'],'unknown');self.assertNotEqual(missing['items'][0]['state'],'resolved')
  changed=ops.reconcile(again,[self.record(condition='service:critical')],later);self.assertEqual(changed['items'][0]['state'],'queued');self.assertIsNone(changed['items'][0]['execution_id'])
  clear=ops.reconcile(again,[self.record('clear')],later);self.assertEqual(clear['items'][0]['source_state'],'clear')
  recurrence=ops.reconcile(clear,[self.record()],later);self.assertEqual(recurrence['items'][0]['state'],'queued')
 def test_unfinished_work_resumes_without_a_second_owner_or_progress_feedback(self):
  state=self.state();later=self.now+dt.timedelta(minutes=16)
  ops.continuation(state,{'items':[]},later,schema);self.assertEqual(state['resume_generation'],1)
  ops.continuation(state,{'items':[]},later+dt.timedelta(minutes=15),schema);self.assertEqual(state['resume_generation'],1)
  ops.continuation(state,{'items':[]},later+dt.timedelta(hours=1),schema);self.assertEqual(state['resume_generation'],2)
  state['items'][0]['state']='waiting';ops.continuation(state,{'items':[]},later+dt.timedelta(hours=2),schema);self.assertEqual(state['resume_generation'],2)
  state['items'][0]['state']='accepted'
  evidence={'items':[{'record_id':'machine-node','state':'accepted','execution_state':'running','execution_liveness':'verified'}]}
  ops.continuation(state,evidence,later+dt.timedelta(hours=2),schema);self.assertEqual(state['resume_generation'],2)
  evidence['items'][0]['execution_state']='failed';evidence['items'][0]['execution_liveness']='not_applicable'
  ops.continuation(state,evidence,later+dt.timedelta(hours=2),schema);self.assertEqual(state['resume_generation'],3)
 def test_stale_unknown_source_cannot_request_an_owner_decision(self):
  state=self.state();state['items'][0].update(source_state='unknown',source_at=(self.now-dt.timedelta(days=7)).isoformat())
  with self.assertRaisesRegex(ValueError,'incident_evidence_stale'):ops.report(state,self.payload(state['items'][0],state='needs_user',blocker='owner_approval',decision='Подтвердить?'),'execution',self.now,schema)
 def test_previous_occurrence_report_cannot_claim_a_recurrence(self):
  state=self.state();payload=self.payload(state['items'][0]);first=state['items'][0]['fingerprint']
  state=ops.reconcile(state,[self.record('clear')],self.now);state=ops.reconcile(state,[self.record()],self.now)
  self.assertNotEqual(state['items'][0]['fingerprint'],first)
  with self.assertRaisesRegex(ValueError,'stale_incident'):ops.report(state,payload,'execution',self.now,schema)
 def test_capacity_is_visible_and_keeps_existing_items(self):
  records=[{**self.record(),'record_id':'machine-'+str(i)} for i in range(200)];state=ops.reconcile({},records,self.now)
  with self.assertRaisesRegex(ValueError,'incident_capacity_exhausted'):ops.reconcile(copy.deepcopy(state),[{**self.record(),'record_id':'new'}],self.now)
  self.assertEqual(len(state['items']),200)
 def test_progress_preserves_existing_plane_identity(self):
  state=self.state();state['items'][0]['task_ref']='TASK-EXAMPLE';payload=self.payload(state['items'][0])
  ops.report(state,payload,'execution',self.now,schema);self.assertEqual(state['items'][0]['task_ref'],'TASK-EXAMPLE')
  payload['task_ref']='OTHER-TASK'
  with self.assertRaisesRegex(ValueError,'task_identity_change'):ops.report(state,payload,'execution',self.now,schema)
 def test_missing_source_suspends_an_old_resolution(self):
  state=self.state();state['items'][0].update(state='resolved',source_state='clear')
  value=ops.reconcile(state,[],self.now);self.assertEqual(value['items'][0]['state'],'waiting');self.assertEqual(value['items'][0]['blocker'],'awaiting_source')
 def test_explicit_decision_stale_report_and_unverified_recovery(self):
  state=self.state();row=state['items'][0]
  for payload in [self.payload(row,state='needs_user',blocker='none'),self.payload(row,state='resolved',blocker='none'),{**self.payload(row),'fingerprint':'0'*64},self.payload(row,state='needs_user',blocker='login_required',decision='Bearer SECRET')]:
   with self.assertRaises(ValueError):ops.report(copy.deepcopy(state),payload,'execution',self.now,schema)
  ops.report(state,self.payload(row,state='needs_user',blocker='login_required',decision='Войдите в тестовый источник.'),'execution',self.now,schema)
  self.assertEqual(state['items'][0]['state'],'needs_user')
 def database(self,root):
  cron=root/'profiles/ops/cron';cron.mkdir(parents=True)
  path=cron/'executions.db'
  with sqlite3.connect(path) as db:
   db.execute('create table executions(id text,pid integer,process_started_at integer,status text,handoff_pending integer)')
   db.execute('insert into executions values (?,?,?,?,?)',('execution',42,123,'running',0))
  return path
 def test_report_requires_real_native_ancestor_and_kernel_incarnation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);path=self.database(root);proc=root/'proc/42';proc.mkdir(parents=True)
   fields=['S','1']+['0']*17+['123'];(proc/'stat').write_text('42 (worker) '+' '.join(fields))
   self.assertEqual(ops.live_execution(path,{42},root/'proc'),'execution')
   with self.assertRaises(ValueError):ops.live_execution(path,{43},root/'proc')
   fields[19]='124';(proc/'stat').write_text('42 (worker) '+' '.join(fields))
   with self.assertRaises(ValueError):ops.live_execution(path,{42},root/'proc')
 def test_read_joins_execution_without_prompts_and_failure_stops_activity(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);dbpath=self.database(root);checkpoint=root/'profiles/ops/checkpoints';checkpoint.mkdir()
   state=self.state();ops.report(state,self.payload(state['items'][0],state='accepted',blocker='none'),'execution',self.now,schema)
   (checkpoint/'dashboard-incidents.json').write_text(json.dumps(state))
   value=cockpit_read.incident_work(root,self.now.isoformat());self.assertEqual(value['status'],'ok');self.assertEqual(value['items'][0]['execution_state'],'running')
   self.assertNotIn('execution_id',json.dumps(value));self.assertNotIn('prompt',json.dumps(value))
   with sqlite3.connect(dbpath) as db:db.execute("update executions set status='failed'")
   value=cockpit_read.incident_work(root,self.now.isoformat());self.assertEqual(value['items'][0]['execution_state'],'failed');self.assertEqual(value['items'][0]['execution_liveness'],'not_applicable')
 def test_waiting_publisher_cannot_write_after_a_paired_rollback(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'cockpit.json').write_text(json.dumps(fixture(self.now)));before=(root/'cockpit.json').read_bytes()
   link=root/'current';link.symlink_to(cockpit_publish.RELEASE_DIRECTORY,target_is_directory=True)
   entered=threading.Event();flock=fcntl.flock
   def observed(fd,how):
    if how==fcntl.LOCK_EX:entered.set()
    return flock(fd,how)
   with (root/'cockpit-publish.lock').open('a') as lock,concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool,patch.object(cockpit_publish,'RELEASE_LINK',link),patch.object(cockpit_publish.fcntl,'flock',side_effect=observed):
    flock(lock,fcntl.LOCK_EX)
    future=pool.submit(cockpit_publish.refresh_local,root,root/'hermes',self.now)
    self.assertTrue(entered.wait(2));link.unlink();link.symlink_to(root,target_is_directory=True)
    flock(lock,fcntl.LOCK_UN);self.assertEqual(future.result(timeout=3)['status'],'stale_release')
   self.assertEqual((root/'cockpit.json').read_bytes(),before)
 def test_local_report_publication_does_not_read_court_or_change_cadence(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);saved=fixture(self.now-dt.timedelta(minutes=10));(root/'cockpit.json').write_text(json.dumps(saved));(root/'cockpit-cadence.json').write_text('{"last_attempt":123}')
   with patch.object(cockpit_publish,'fetch_court',side_effect=AssertionError('External read')),patch.object(cockpit_publish,'RELEASE_LINK',cockpit_publish.RELEASE_DIRECTORY):
    result=cockpit_publish.refresh_local(root,root/'hermes',self.now)
   self.assertEqual(result['status'],'local_published');value=json.loads((root/'cockpit.json').read_text());self.assertEqual(value['court'],saved['court']);self.assertEqual((root/'cockpit-cadence.json').read_text(),'{"last_attempt":123}')

if __name__=='__main__':unittest.main()
