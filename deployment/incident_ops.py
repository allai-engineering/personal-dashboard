"""Existing ops checkpoint/report bridge; fixed cached sources and native execution evidence."""
import datetime as dt,fcntl,hashlib,importlib.util,json,os,pathlib,sqlite3,subprocess,sys,tempfile
P=pathlib.Path
RELEASE=P('/opt/cpa-dashboard/current');HOME=P('/var/lib/hermes/.hermes');CHECKPOINT=HOME/'profiles/ops/checkpoints/dashboard-incidents.json'

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def atomic(path,value):
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  os.fchmod(f.fileno(),0o600);f.write(json.dumps(value,allow_nan=False).encode());f.flush();os.fsync(f.fileno())
 os.replace(f.name,path)

def reconcile(previous,records,now):
 items={w['record_id']:w for w in previous.get('items',[])};stamp=now.isoformat()
 if len(records)>200:raise ValueError('incident_count')
 present=set()
 for r in records:
  key=r['record_id'];present.add(key)
  if r['source_state'] not in ('open','unknown','clear'):raise ValueError('source_state')
  old=items.get(key)
  if r['source_state']=='clear':
   if old:old.update(source_state='clear',source_at=r['source_at'])
   continue
  fingerprint=hashlib.sha256(json.dumps([key,r['condition_key'],stamp,old.get('fingerprint') if old else None]).encode()).hexdigest()
  if old and old['condition_key']==r['condition_key'] and old['source_state']!='clear':
   old.update(source_state=r['source_state'],source_at=r['source_at']);continue
  items[key]={**r,'fingerprint':fingerprint,'queued_at':stamp,'updated_at':stamp,'state':'queued','action':'diagnose','blocker':'none','decision':None,'task_ref':old.get('task_ref') if old else None,'execution_id':None}
 # Missing evidence preserves the incident and suspends decisions; it is never recovery.
 for key,w in items.items():
  if key not in present:
   w['source_state']='unknown'
   if w['state']=='resolved':w.update(state='waiting',action='verify_recovery',blocker='awaiting_source',decision=None)
 if len(items)>200:raise ValueError('incident_capacity_exhausted')
 return {'schema':1,'observed_at':stamp,'items':list(items.values())}

def live_execution(db_path,ancestors=None,proc=P('/proc')):
 if ancestors is None:
  ancestors=set();pid=os.getpid()
  for _ in range(64):
   if pid<=1 or pid in ancestors:break
   ancestors.add(pid)
   try:pid=int((proc/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[1])
   except (OSError,ValueError,IndexError):break
 with sqlite3.connect('file:'+str(db_path)+'?mode=ro',uri=True,timeout=3) as db:
  db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
  rows=list(db.execute("select id,pid,process_started_at from executions where status in ('running','claimed') and handoff_pending=0 order by rowid desc limit 30"))
 for row in rows:
  if row['pid'] in ancestors:
   try:
    parts=(proc/str(row['pid'])/'stat').read_text().rsplit(')',1)[1].split()
    if parts[0]!='Z' and int(parts[19])==int(row['process_started_at']):return row['id']
   except (OSError,ValueError,TypeError,IndexError):pass
 raise ValueError('native_ops_execution_required')

def report(state,payload,execution_id,now,schema):
 if set(payload)!={'record_id','fingerprint','state','action','blocker','decision','task_ref'}:raise ValueError('report_fields')
 row=next((w for w in state['items'] if w['record_id']==payload['record_id']),None)
 if row is None or row['fingerprint']!=payload['fingerprint']:raise ValueError('stale_incident')
 if row.get('task_ref') and payload['task_ref'] not in (None,row['task_ref']):raise ValueError('task_identity_change')
 payload={**payload,'task_ref':payload['task_ref'] or row.get('task_ref')}
 candidate={**row,**payload,'execution_id':execution_id,'updated_at':now.isoformat()}
 public={k:v for k,v in candidate.items() if k!='execution_id'}
 public.update(execution_key=hashlib.sha256(('ops:'+execution_id).encode()).hexdigest()[:24],execution_state='running',execution_liveness='verified')
 schema.validate({'status':'ok','observed_at':now.isoformat(),'items':[public]})
 if candidate['state']=='queued':raise ValueError('report_requires_result')
 if candidate['state']=='resolved' and not -60<=(now-schema.stamp(row['source_at'])).total_seconds()<1800:raise ValueError('recovery_evidence_stale')
 row.update(candidate);return state

def main():
 if len(sys.argv)!=2 or sys.argv[1] not in ('scan','status','report'):raise ValueError('fixed_action')
 CHECKPOINT.parent.mkdir(mode=0o700,exist_ok=True)
 reader=module('incident_reader',RELEASE/'cockpit_read.py');schema=module('incident_schema',RELEASE/'incident_schema.py')
 with CHECKPOINT.with_suffix('.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);now=dt.datetime.now(dt.timezone.utc)
  previous=reader.read(CHECKPOINT,524288) or {'schema':1,'items':[]}
  if sys.argv[1]=='scan':
   server=module('incident_source',RELEASE/'server.py');snapshot=server.SnapshotFile(P('/var/lib/cpa-dashboard/snapshot.json'),cockpit_path=P('/var/lib/cpa-dashboard/cockpit/cockpit.json')).get()
   body=json.dumps(snapshot,allow_nan=False).encode()
   run=subprocess.run(['/usr/local/bin/node',str(RELEASE/'incident_intake.mjs')],input=body,capture_output=True,timeout=12)
   if run.returncode or len(run.stdout)>524288:raise ValueError('intake_failed')
   value=reconcile(previous,json.loads(run.stdout),now);atomic(CHECKPOINT,value)
   print(json.dumps({'intake':sorted([w['record_id'],w['fingerprint']] for w in value['items'] if w['source_state']!='clear')}));return
  if sys.argv[1]=='status':
   print(json.dumps(previous));return
  raw=sys.stdin.buffer.read(8193)
  if len(raw)>8192:raise ValueError('report_size')
  execution=live_execution(HOME/'profiles/ops/cron/executions.db')
  value=report(previous,json.loads(raw),execution,now,schema);atomic(CHECKPOINT,value)
 # Refresh only local execution/checkpoint evidence after a report; external cadence is untouched.
 publisher=module('incident_publisher',RELEASE/'cockpit_publish.py')
 publisher.refresh_local(P('/var/lib/cpa-dashboard/cockpit'),HOME)
 print(json.dumps({'recorded':True,'execution_key':hashlib.sha256(('ops:'+execution).encode()).hexdigest()[:24]}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'error':str(e) if isinstance(e,ValueError) and str(e).replace('_','').isalnum() else type(e).__name__}));raise SystemExit(1)
