import atexit,copy,datetime as dt,io,json,pathlib,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
BUNDLE=tempfile.TemporaryDirectory();atexit.register(BUNDLE.cleanup)
ROOT=pathlib.Path(__file__).parent
shutil.copy2(ROOT/'deployment/mac_battery.py',pathlib.Path(BUNDLE.name)/'mac_battery.py')
shutil.copy2(ROOT/'release/battery_schema.py',pathlib.Path(BUNDLE.name)/'battery_schema.py')
sys.path.insert(0,BUNDLE.name)
import mac_battery as b

class Tests(unittest.TestCase):
 def setUp(self):self.now=dt.datetime.now(dt.timezone.utc)
 def sample(self):
  profile={'SPPowerDataType':[{'sppower_battery_charge_info':{'sppower_battery_state_of_charge':100,'sppower_battery_is_charging':'FALSE'},'sppower_battery_health_info':{'sppower_battery_cycle_count':0,'sppower_battery_health':'Good','sppower_battery_health_maximum_capacity':'89\u00a0%'}}]}
  return b.from_power(profile,{'status':'ok','limit_percent':80,'limit_enabled':True},self.now)
 def test_native_setting_is_separate_from_charge_and_health(self):
  s=self.sample();self.assertEqual((s['charge_percent'],s['health_percent'],s['cycle_count']),(100,89,0));self.assertTrue(s['limit_enabled']);self.assertEqual(s['limit_percent'],80)
 def test_unknown_power_fields_are_not_zero(self):
  for profile in [{},{'SPPowerDataType':[]},{'SPPowerDataType':[{'sppower_battery_charge_info':None,'sppower_battery_health_info':None}]}]:
   s=b.from_power(profile,None,self.now)
   self.assertTrue(all(s[k] is None for k in b._schema.METRICS));self.assertEqual(s['health_condition'],'unknown')
 def test_invalid_fields_fail_closed(self):
  s=self.sample()
  for key,value in [('charge_percent',True),('health_percent',101),('health_percent',-1),('cycle_count',float('inf')),('limit_enabled',1),('health_condition','SECRET'),('api_key','SECRET')]:
   bad=copy.deepcopy(s);bad[key]=value
   with self.subTest(key=key,value=value),self.assertRaises(ValueError):b.validate(bad)
  for status in ['unreachable','not_connected','unavailable']:
   bad=copy.deepcopy(s);bad['status']=status
   with self.assertRaises(ValueError):b.validate(bad)
   self.assertIsNone(b.validate(b.empty(status))['limit_percent'])
 def test_native_unknown_and_disabled_are_distinct(self):
  s=self.sample();s.update(limit_status='unsupported',limit_percent=None,limit_enabled=None);b.validate(s)
  s.update(limit_status='ok',limit_percent=80,limit_enabled=False);b.validate(s)
  s.update(limit_enabled=None)
  with self.assertRaises(ValueError):b.validate(s)
 def config(self,path):
  v={'schema':1,'sources':[{'id':'node-a','ssh_host':'node-a','hardware_hash':'a'*64},{'id':'node-b','ssh_host':None,'hardware_hash':None}]};path.write_text(json.dumps(v));return v
 def test_cache_interval_failure_and_route_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=pathlib.Path(tmp)/'sources.json';cache=pathlib.Path(tmp)/'cache.json';config=self.config(c)
   with patch.object(b,'pull',return_value=self.sample()) as read:
    b.collect(c,cache,self.now);self.assertEqual(read.call_count,2)
    b.collect(c,cache,self.now+dt.timedelta(seconds=899));self.assertEqual(read.call_count,2)
    config['sources'][0]['hardware_hash']='b'*64;c.write_text(json.dumps(config));b.collect(c,cache,self.now+dt.timedelta(seconds=899));self.assertEqual(read.call_count,4)
   with patch.object(b,'pull',return_value=b.empty('unreachable',self.now.isoformat())) as read:
    result=b.collect(c,cache,self.now+dt.timedelta(seconds=1800));self.assertEqual(read.call_count,2)
    self.assertIsNone(result['node-a']['limit_percent']);self.assertEqual(result['node-a']['status'],'unreachable')
    b.collect(c,cache,self.now+dt.timedelta(seconds=1801));self.assertEqual(read.call_count,2)
 def test_config_does_not_select_arbitrary_commands(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=pathlib.Path(tmp)/'sources.json';cache=pathlib.Path(tmp)/'cache.json';config=self.config(c);config['sources'][0]['ssh_host']='node-a; set80';c.write_text(json.dumps(config))
   with patch.object(b,'pull') as read:self.assertEqual(b.collect(c,cache,self.now),{});read.assert_not_called()
 def test_invalid_cache_shape_is_rebuilt(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=pathlib.Path(tmp)/'sources.json';cache=pathlib.Path(tmp)/'cache.json';self.config(c)
   with patch.object(b,'pull',return_value=self.sample()) as read:
    b.collect(c,cache,self.now);cached=json.loads(cache.read_text());cached['machines']=['node-a','node-b'];cache.write_text(json.dumps(cached))
    result=b.collect(c,cache,self.now+dt.timedelta(seconds=1));self.assertEqual(read.call_count,4);self.assertEqual(result['node-a']['limit_percent'],80)
 def test_ssh_protocol_identity_size_and_freshness(self):
  source={'id':'node-a','ssh_host':'node-a','hardware_hash':'a'*64}
  valid={'schema':1,'id':'node-a','hardware_hash':'a'*64,'battery':self.sample()}
  class Process:
   pid=1
   def __init__(self,body):self.stdout=io.BytesIO(body)
   def wait(self,**_):return 0
   def poll(self):return 0
  variants=[valid,{**valid,'id':'other'},{**valid,'hardware_hash':'b'*64},{**valid,'schema':True},{**valid,'secret':'SECRET'},{**valid,'battery':{**self.sample(),'observed_at':(self.now-dt.timedelta(minutes=3)).isoformat()}}]
  for i,v in enumerate(variants):
   with patch.object(b.subprocess,'Popen',return_value=Process(json.dumps(v).encode())) as run:
    result=b.pull(source,self.now);self.assertEqual(result['status'],'ok' if i==0 else 'unreachable')
    self.assertEqual(run.call_args.args[0],['/usr/bin/ssh','-F','/etc/cpa-dashboard/readers/ssh_config','-T','node-a','battery'])
  with patch.object(b.subprocess,'Popen',return_value=Process(b'x'*32769)):
   self.assertEqual(b.pull(source,self.now)['status'],'unreachable')
 def test_reader_rejects_write_arguments(self):
  script=pathlib.Path(b.__file__)
  p=subprocess.run([sys.executable,'-I',str(script),'set80'],capture_output=True)
  self.assertEqual(p.returncode,64);self.assertEqual(p.stdout,b'')

if __name__=='__main__':unittest.main()
