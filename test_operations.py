import copy,datetime as dt,importlib.util,json,pathlib,sys,unittest
RELEASE=pathlib.Path(__file__).resolve().parent/'release'
sys.path.insert(0,str(RELEASE))
import operations as o
class Tests(unittest.TestCase):
 def setUp(self):self.now=dt.datetime(2026,10,30,12,tzinfo=dt.timezone.utc)
 def test_balances_use_provider_semantics(self):
  self.assertEqual(o.balance('openrouter',{'data':{'total_credits':200,'total_usage':25}},self.now)['remaining'],175)
  self.assertEqual(o.balance('kie',{'code':200,'data':0},self.now)['remaining'],0)
  d=o.balance('digitalocean',{'account_balance':'-1250.00','month_to_date_usage':'154.39','month_to_date_balance':'-1095.61','generated_at':self.now.isoformat()},self.now)
  self.assertEqual(d['remaining'],1095.61);self.assertEqual(d['accrued_due'],0)
  d=o.balance('digitalocean',{'account_balance':'0','month_to_date_usage':'154.39','month_to_date_balance':'154.39','generated_at':self.now.isoformat()},self.now)
  self.assertEqual(d['remaining'],0);self.assertEqual(d['accrued_due'],154.39)
 def test_missing_malformed_auth_and_bool_never_zero(self):
  for x in [None,True,'0',float('nan'),float('inf'),-1]:
   with self.subTest(x=x),self.assertRaises(ValueError):o.balance('kie',{'code':200,'data':x},self.now)
  for d in [{'code':401,'data':0},{'code':True,'data':0},{'code':200}]:
   with self.assertRaises((ValueError,KeyError)):o.balance('kie',d,self.now)
  self.assertIsNone(o.unavailable_balance('kie','auth_error',self.now)['remaining'])
  with self.assertRaises(ValueError):o.balance('digitalocean',{'account_balance':'1','month_to_date_usage':'2','month_to_date_balance':'1','generated_at':self.now.isoformat()},self.now)
 def make_fleet(self):
  t=self.now.isoformat()
  inv={'schema':1,'machines':[{'id':'main','enabled':True,'kind':'physical_mac','address':'SECRET_ADDRESS'},{'id':'missing','enabled':False}]}
  latest={'schema':1,'observed_at':t,'machines':[{'id':'main','state':'degraded','issues':[{'check':'disk:/','severity':'critical','detail':'SECRET_BODY'},{'check':'disk:/data','severity':'critical'}],'probe':{'hostname':'SECRET_HOST','observed_at':t,'checks':{'disk:/':{'free_percent':2},'processes':['SECRET_COMMAND']}}}]}
  current={'schema':1,'observed_at':t,'monitor_observed_at':t,'summary':{'issues':[{'machine':'main','check':'kuma:1','severity':'warning','detail':'SECRET_URL'}]}}
  return o.fleet(inv,latest,current,self.now)
 def test_fleet_dedup_and_allowlist(self):
  f=self.make_fleet();self.assertEqual(f['inventory_count'],2);self.assertEqual(f['enrolled'],1)
  main,missing=f['machines'];self.assertEqual(main['metrics']['disk_free_percent'],2)
  self.assertEqual(len(main['issues']),2);self.assertEqual(missing['state'],'unknown')
  self.assertIsNone(missing['metrics']['disk_free_percent']);self.assertNotIn('SECRET',json.dumps(f))
 def test_freshness_is_source_time_and_future_fails(self):
  self.assertFalse(o.fresh((self.now-dt.timedelta(hours=8)).isoformat(),self.now,25200))
  self.assertFalse(o.fresh((self.now+dt.timedelta(hours=1)).isoformat(),self.now,25200))
  self.assertFalse(o.fresh(None,self.now,25200))
 def test_protocol_rejects_extra_fields_and_unknown_as_zero(self):
  d={'schema':o.SCHEMA,'read_only':True,'collected_at':self.now.isoformat(),'balances':[o.unavailable_balance(p,'unavailable',self.now) for p in o.PROVIDERS],'fleet':self.make_fleet()}
  o.validate(d)
  for path in ['top','balance','machine','metrics']:
   bad=copy.deepcopy(d)
   target={'top':bad,'balance':bad['balances'][0],'machine':bad['fleet']['machines'][0],'metrics':bad['fleet']['machines'][0]['metrics']}[path]
   target['api_key']='SECRET'
   with self.subTest(path=path),self.assertRaises(ValueError):o.validate(bad)
  d['balances'][0]['remaining']=0
  with self.assertRaises(ValueError):o.validate(d)
if __name__=='__main__':unittest.main()
