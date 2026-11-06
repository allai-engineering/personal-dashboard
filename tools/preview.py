"""Local browser-test preview. Synthetic accounts only; never connects to a provider."""
import argparse, datetime as dt, hashlib, json, pathlib, sys, types
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'release'))
import server
from mail_secretary import validate

mail_decisions={}
def mail_fixture(value):
 if value['operation']=='evidence' and value['case_id']=='2'*32:return {'observed_at':'2026-10-05T12:00:00+00:00','deadline':None,'kind':'waiting_reply','sources':['b'*32],'excerpt':'Please send the signed document.','status':'verified_excerpt'}
 if value['operation']=='history':return {'events':[{'event':'incoming_request','at':'2026-11-04T08:00:00Z','ref':'b'*32},{'event':'reminder_cancelled','at':'2026-11-04T10:00:00Z','reason':'reply_received','ref':'c'*32}],'omitted':0,'legacy':False}
 if value["operation"]=="evidence":return {"observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),"deadline":"2026-11-09","kind":"renewal","sources":["b"*32],"excerpt":"Synthetic renewal notice: renews 2026-11-09. <script>untrusted</script>","status":"verified_excerpt"}
 if value["operation"]=="action":
  current=mail_decisions.get(value["case_id"])
  if value["expected"] != (current["request_id"] if current else None):return {"error":"decision_conflict"}
  mail_decisions[value["case_id"]]={k:value[k] for k in ("action","remind_on","request_id")}
  mail_decisions[value["case_id"]].update(at=dt.datetime.now(dt.timezone.utc).isoformat(),status={"resolved":"resolved","remind":"snoozed","investigate":"queued"}[value["action"]])
 return {"available":True,"decisions":mail_decisions}


def fixture():
 now=dt.datetime.now(dt.timezone.utc);t=now.isoformat();reset=(now+dt.timedelta(days=2)).isoformat()
 mail=validate(json.loads((pathlib.Path(__file__).resolve().parents[1]/'tests/fixtures/mail-outcomes.json').read_text()))
 mail['checked_at']=t
 for row in mail['cases']:row['updated_at']=t
 cockpit={'schema':'captain-cockpit-v1','collected_at':t,'read_only':True,'court':{'status':'partial','observed_at':t,'receipt_status':'ok','receipt_scope':'kad_metadata','receipt_observed_at':t,'changes':0,'important':0,'unverified':1,'carried_forward':2,'search_status':'incomplete','confirmed_dates_available':False,'known_cases':26},'profiles':[{'id':'ops','status':'ok','stored_jobs':1},{'id':'lawyer','status':'ok','stored_jobs':1}],'tasks':[],'events':[]}
 for ident,state,origin in [('scheduled','failed','scheduled'),('manual','completed','manual'),('unverified','running','scheduled')]:
  cockpit['tasks'].append({'id':ident,'job_key':'court-check' if ident!='unverified' else 'ops-check','profile':'lawyer' if ident!='unverified' else 'ops','label':'Synthetic court check' if ident!='unverified' else 'Synthetic operations check','state':state,'origin':origin,'claimed_at':t,'started_at':t,'finished_at':t if state!='running' else None,'progress_at':None,'observed_at':t,'liveness':'unverified' if state=='running' else 'not_applicable','next_run_at':None,'has_error':state=='failed','enabled':True})
 cockpit['work']={'status':'ok','observed_at':t,'items':[]}
 for aid,band in [('critical','critical'),('low','low')]:
  cockpit['work']['items'].append({'record_id':'quota-'+aid+'-secondary_window-10080','condition_key':'quota:'+band,'fingerprint':hashlib.sha256(('quota:'+band).encode()).hexdigest(),'source_state':'open','source_at':t,'queued_at':t,'updated_at':t,'state':'needs_user','action':'check_source','blocker':'owner_approval','decision':'Выбрать другой тестовый аккаунт?','task_ref':None,'execution_key':'a'*24,'execution_state':'completed','execution_liveness':'not_applicable'})
 def account(ident,remaining):
  return {'id':ident,'label':'Fixture '+ident,'provider':'codex','inventory_present':True,'status':'active','disabled':False,'unavailable':False,'cooldowns':{'status':'ok','items':[]},'subscription':{'plan':'pro','active_until':None},'quota':{'observed_at':t,'windows':[{'slot':'secondary_window','window_minutes':10080,'remaining_percent':remaining,'reset_at':reset},{'slot':'primary_window','window_minutes':300,'remaining_percent':70,'reset_at':(now+dt.timedelta(hours=2)).isoformat()}]},'windows':{}}
 accounts=[account('critical',8),account('low',20),account('healthy',80),account('unknown',None)]
 retired=account('disabled',0);retired['disabled']=True
 auth=account('authorization',None);auth['data_problem']='Сессия Claude истекла'
 return {'mail_secretary':mail,'cockpit':cockpit,'schema':'cpa-account-dashboard-v1','observed_at_utc':t,'read_only':True,'generation_requests_sent':0,'status':'ok','inventory':{'status':'ok','complete':True,'listed_accounts':6},'accounts':accounts+[retired,auth],'observed_orphans':[],'cache':{'stale':False,'last_error':None},'external':{'sources':[],'hostkey_identity_map':{},'account_logins':{a['id']:a['id']+'@example.test' for a in accounts+[auth]}},'runtime':{'policy':{'max-retry-interval':5,'stream_start_timeout':'120s','transient-error-cooldown-seconds':15}},'operations':{'schema':'personal-dashboard-operations-v1','collected_at':t,'read_only':True,'balances':[{'id':'openrouter','title':'OpenRouter','unit':'USD','remaining':12,'status':'ok','source_at':t,'observed_at':t,'month_spend':None,'accrued_due':None,'account_balance':None},{'id':'kie','title':'Kie','unit':'credits','remaining':None,'status':'unavailable','source_at':None,'observed_at':t,'month_spend':None,'accrued_due':None,'account_balance':None}],'fleet':{'status':'ok','observed_at':t,'inventory_count':1,'enrolled':1,'machines':[{'id':'fixture-host','kind':'cloud_vm','state':'observed_ok','observed_at':t,'metrics':{},'issues':[]}] }},'integrations':{'schema':1,'collected_at':t,'integrations':[]}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8877);args=p.parse_args()
 salt=bytes.fromhex('a1'*32);key=bytes.fromhex('b2'*32)
 auth=server.PasswordAuth(b'fixture',hashlib.pbkdf2_hmac('sha256',b'fixture-only-browser-password',salt,600000),salt,key)
 web=server.DashboardServer(('127.0.0.1',args.port),server.Handler)
 server.mail_control=mail_fixture
 web.auth=auth;web.public_origin='http://127.0.0.1:'+str(args.port);web.snapshot_cache=types.SimpleNamespace(get=fixture)
 web.serve_forever()
if __name__=='__main__':main()
