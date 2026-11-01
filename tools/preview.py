"""Local browser-test preview. Synthetic accounts only; never connects to a provider."""
import argparse, datetime as dt, hashlib, pathlib, sys, types
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'release'))
import server

def fixture():
 now=dt.datetime.now(dt.timezone.utc);t=now.isoformat();reset=(now+dt.timedelta(days=2)).isoformat()
 def account(ident,remaining):
  return {'id':ident,'label':'Fixture '+ident,'provider':'codex','inventory_present':True,'status':'active','disabled':False,'unavailable':False,'cooldowns':{'status':'ok','items':[]},'subscription':{'plan':'pro','active_until':None},'quota':{'observed_at':t,'windows':[{'slot':'secondary_window','window_minutes':10080,'remaining_percent':remaining,'reset_at':reset},{'slot':'primary_window','window_minutes':300,'remaining_percent':70,'reset_at':(now+dt.timedelta(hours=2)).isoformat()}]},'windows':{}}
 accounts=[account('critical',8),account('low',20),account('healthy',80),account('unknown',None)]
 retired=account('disabled',0);retired['disabled']=True
 auth=account('authorization',None);auth['data_problem']='Сессия Claude истекла'
 return {'schema':'cpa-account-dashboard-v1','observed_at_utc':t,'read_only':True,'generation_requests_sent':0,'status':'ok','inventory':{'status':'ok','complete':True,'listed_accounts':6},'accounts':accounts+[retired,auth],'observed_orphans':[],'cache':{'stale':False,'last_error':None},'external':{'sources':[],'hostkey_identity_map':{},'account_logins':{a['id']:a['id']+'@example.test' for a in accounts+[auth]}},'runtime':{'policy':{'max-retry-interval':5,'stream_start_timeout':'120s','transient-error-cooldown-seconds':15}},'operations':{'schema':'personal-dashboard-operations-v1','collected_at':t,'read_only':True,'balances':[{'id':'openrouter','title':'OpenRouter','unit':'USD','remaining':12,'status':'ok','source_at':t,'observed_at':t,'month_spend':None,'accrued_due':None,'account_balance':None},{'id':'kie','title':'Kie','unit':'credits','remaining':None,'status':'unavailable','source_at':None,'observed_at':t,'month_spend':None,'accrued_due':None,'account_balance':None}],'fleet':{'status':'ok','observed_at':t,'inventory_count':1,'enrolled':1,'machines':[{'id':'fixture-host','kind':'cloud_vm','state':'observed_ok','observed_at':t,'metrics':{},'issues':[]}] }},'integrations':{'schema':1,'collected_at':t,'integrations':[]}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8877);args=p.parse_args()
 salt=bytes.fromhex('a1'*32);key=bytes.fromhex('b2'*32)
 auth=server.PasswordAuth(b'fixture',hashlib.pbkdf2_hmac('sha256',b'fixture-only-browser-password',salt,600000),salt,key)
 web=server.DashboardServer(('127.0.0.1',args.port),server.Handler)
 web.auth=auth;web.public_origin='http://127.0.0.1:'+str(args.port);web.snapshot_cache=types.SimpleNamespace(get=fixture)
 web.serve_forever()
if __name__=='__main__':main()
