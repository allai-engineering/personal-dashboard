import copy,datetime as dt,hashlib,json,pathlib,tempfile,unittest
import cockpit_read,incident_schema
from deployment import incident_ops

class InfraProgress(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.now=dt.datetime.now(dt.timezone.utc)
  state=incident_ops.reconcile({},[{'record_id':'machine-node','condition_key':'service:warning','source_state':'open','source_at':self.now.isoformat()}],self.now);r=state['items'][0]
  args={'record_id':r['record_id'],'fingerprint':r['fingerprint'],'state':'accepted','action':'diagnose','blocker':'none','decision':None,'task_ref':None};incident_ops.report(state,args,'parent',self.now,incident_schema);self.raw=r
  self.item={k:v for k,v in r.items() if k not in ('execution_id','subject')};self.item.update(execution_key='a'*24,execution_state='running',execution_liveness='verified')
  key=hashlib.sha256((r['record_id']+'\0'+r['fingerprint']).encode()).hexdigest();self.path=self.root/'profiles/ops/checkpoints/infra-handoffs'/(key+'.json');self.path.parent.mkdir(parents=True)
  self.phase={'schema':1,'profile':'infra-dev','record_id':r['record_id'],'fingerprint':r['fingerprint'],'parent_execution_id':'parent','owner_snapshot':{k:r.get(k) for k in ('execution_id','state','action','blocker','decision','task_ref','updated_at','fingerprint')},'native_task_id':'sa-0-abcdef01','state':'waiting','action':'test_fix','blocker':'awaiting_source','decision':None,'task_ref':None,'updated_at':(self.now+dt.timedelta(seconds=1)).isoformat()}
 def overlay(self):
  self.path.write_text(json.dumps(self.phase));return cockpit_read.infra_overlay(self.root,self.raw,self.item,incident_schema,(self.now+dt.timedelta(seconds=2)).isoformat())
 def test_actual_phase_is_visible_and_native_identifiers_stay_private(self):
  v=self.overlay();self.assertEqual(v['actor'],'infra-dev');self.assertEqual(v['state'],'waiting');self.assertEqual(v['action'],'test_fix');self.assertNotIn('native_task_id',v);self.assertNotIn('parent_execution_id',v)
 def test_preparation_is_historical_evidence_and_never_changes_incident_state(self):
  report={'schema':1,'items':[{'record_id':self.raw['record_id'],'fingerprint':self.raw['fingerprint'],'status':'passed_conditional','tested_at':self.now.isoformat(),'checks':17,'private_prompt':'fixture-private-text'}]}
  target=self.path.parent.parent/'infra-results.json';target.write_text(json.dumps(report))
  value=cockpit_read.preparation_overlay(cockpit_read.read(target),self.item,incident_schema,self.now.isoformat())
  self.assertEqual(value['preparation'],{'status':'passed_conditional','tested_at':self.now.isoformat(),'checks':17,'current_occurrence':True})
  self.assertEqual(value['state'],self.item['state']);self.assertEqual(value['blocker'],self.item['blocker'])
  self.assertNotIn('fixture-private-text',json.dumps(value))
  report['items'][0]['fingerprint']='b'*64;target.write_text(json.dumps(report))
  value=cockpit_read.preparation_overlay(cockpit_read.read(target),self.item,incident_schema,self.now.isoformat())
  self.assertFalse(value['preparation']['current_occurrence'])
 def test_unverified_or_malformed_preparation_does_not_hide_current_progress(self):
  target=self.path.parent.parent/'infra-results.json'
  report={'record_id':self.raw['record_id'],'fingerprint':self.raw['fingerprint'],'status':'passed_conditional','tested_at':self.now.isoformat(),'checks':17}
  for changes in ({'status':'production_ready'},{'checks':True},{'checks':0},{'tested_at':(self.now+dt.timedelta(hours=1)).isoformat()}):
   target.write_text(json.dumps({'schema':1,'items':[{**report,**changes}]}))
   self.assertEqual(cockpit_read.preparation_overlay(cockpit_read.read(target),self.item,incident_schema,self.now.isoformat()),self.item)
  target.write_text(json.dumps({'schema':1,'items':[report,report]}))
  self.assertEqual(cockpit_read.preparation_overlay(cockpit_read.read(target),self.item,incident_schema,self.now.isoformat()),self.item)
 def test_pending_wrong_owner_old_version_and_old_phase_do_not_replace_owner(self):
  for key,value in [('native_task_id',None),('parent_execution_id','other'),('fingerprint','b'*64),('updated_at',(self.now-dt.timedelta(seconds=1)).isoformat())]:
   phase=copy.deepcopy(self.phase);self.phase[key]=value;self.assertEqual(self.overlay(),self.item);self.phase=phase
 def test_false_recovery_private_fields_and_invalid_blockers_do_not_promote_progress(self):
  for changes in [{'state':'resolved','blocker':'none'},{'state':'needs_user','blocker':'no_safe_procedure','decision':'Investigate'},{'blocker':'secret-string'},{'action':'shell command'}]:
   phase=copy.deepcopy(self.phase);self.phase.update(changes);self.assertEqual(self.overlay(),self.item);self.phase=phase
 def test_actor_is_optional_and_cannot_name_an_arbitrary_actor(self):
  incident_schema.validate({'status':'ok','observed_at':self.now.isoformat(),'items':[self.item]})
  with self.assertRaisesRegex(ValueError,'incident_actor'):incident_schema.validate({'status':'ok','observed_at':self.now.isoformat(),'items':[{**self.item,'actor':'some-provider'}]})
 def test_later_owner_result_wins_over_a_later_child_timestamp(self):
  self.raw.update(state='waiting',blocker='no_safe_procedure');self.assertEqual(self.overlay(),self.item)
 def test_missing_or_malformed_infra_jobs_remain_unknown(self):
  def profile():return next(x for x in cockpit_read.hermes(self.root)['profiles'] if x['id']=='infra-dev')
  self.assertEqual(profile()['status'],'unavailable');self.assertIsNone(profile()['stored_jobs'])
  jobs=self.root/'profiles/infra-dev/cron/jobs.json';jobs.parent.mkdir(parents=True);jobs.write_text('{"jobs": []}')
  self.assertEqual(profile()['status'],'empty');self.assertEqual(profile()['stored_jobs'],0)
  for invalid in [None,{}, {'id':None}]:
   jobs.write_text(json.dumps({'jobs':[invalid]}));self.assertEqual(profile()['status'],'unavailable');self.assertIsNone(profile()['stored_jobs'])
  jobs.write_text('{"jobs": "invalid"}');self.assertEqual(profile()['status'],'unavailable');self.assertIsNone(profile()['stored_jobs'])

if __name__=='__main__':unittest.main()
