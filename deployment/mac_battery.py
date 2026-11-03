"""Bounded read-only Mac battery reader and SSH collector; outside the web runtime."""
import concurrent.futures, datetime as dt, hashlib, importlib.util, json, os, pathlib, platform
import plistlib, re, signal, subprocess, sys, tempfile, threading
P=pathlib.Path
INTERVAL=900
SLUG=re.compile(r'[A-Za-z0-9_.-]{1,80}')
_spec=importlib.util.spec_from_file_location('battery_data_contract',P(__file__).with_name('battery_schema.py'))
_schema=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_schema)
empty,validate,instant=_schema.empty,_schema.validate,_schema.instant

def numeric(value,maximum=100):
    return value if type(value) is int and 0<=value<=maximum else None

def from_power(profile,limit,now):
    value=empty('ok',now.isoformat());value['observed_at']=now.isoformat()
    rows=profile.get('SPPowerDataType') if isinstance(profile,dict) else None
    power=rows[0] if isinstance(rows,list) and rows and isinstance(rows[0],dict) else {}
    charge=power.get('sppower_battery_charge_info',{});health=power.get('sppower_battery_health_info',{})
    if not isinstance(charge,dict):charge={}
    if not isinstance(health,dict):health={}
    value['charge_percent']=numeric(charge.get('sppower_battery_state_of_charge'))
    value['is_charging']={'TRUE':True,'FALSE':False}.get(charge.get('sppower_battery_is_charging'))
    value['cycle_count']=numeric(health.get('sppower_battery_cycle_count'),100000)
    raw=health.get('sppower_battery_health_maximum_capacity')
    match=re.fullmatch(r'\s*(?:(\d{1,3})\s*%|%\s*(\d{1,3}))\s*',raw) if isinstance(raw,str) else None
    value['health_percent']=numeric(int(match[1] or match[2])) if match else None
    value['health_condition']={'Good':'normal','Normal':'normal','Service Recommended':'service_recommended','Check Battery':'service_recommended'}.get(health.get('sppower_battery_health'),'unknown')
    if isinstance(limit,dict) and set(limit)=={'status','limit_percent','limit_enabled'} and limit['status'] in ('ok','unsupported','unavailable'):
        value.update(limit_status=limit['status'],limit_percent=limit['limit_percent'],limit_enabled=limit['limit_enabled'])
    return validate(value)

def local():
    if len(sys.argv)!=1 or os.environ.get('SSH_ORIGINAL_COMMAND','') not in ('','battery') or platform.system()!='Darwin': raise SystemExit(64)
    config=json.loads(P(__file__).with_name('battery-source.json').read_text())
    if set(config)!={'id'} or not SLUG.fullmatch(config['id']): raise ValueError('source_config')
    hardware=plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg','-rd1','-c','IOPlatformExpertDevice','-a'],timeout=3))[0]['IOPlatformUUID']
    try:
        power=json.loads(subprocess.check_output(['/usr/sbin/system_profiler','SPPowerDataType','-json'],env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','LC_ALL':'C'},timeout=6))
    except (OSError,ValueError,subprocess.SubprocessError): power={}
    try:
        limit=json.loads(subprocess.check_output([str(P(__file__).with_name('mac-battery-native'))],stderr=subprocess.DEVNULL,timeout=6))
    except (OSError,ValueError,subprocess.SubprocessError): limit=None
    now=dt.datetime.now(dt.timezone.utc)
    print(json.dumps({'schema':1,'id':config['id'],'hardware_hash':hashlib.sha256(hardware.encode()).hexdigest(),'battery':from_power(power,limit,now)},allow_nan=False))

def pull(source,now):
    if source['ssh_host'] is None: return empty('not_connected',now.isoformat())
    command=['/usr/bin/ssh','-F','/etc/cpa-dashboard/readers/ssh_config','-T',source['ssh_host'],'battery']
    process=None;timer=None
    def kill():
        if process is not None and process.poll() is None:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    try:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
        timer=threading.Timer(12,kill);timer.start();body=process.stdout.read(32769)
        if len(body)>32768 or process.wait(timeout=1): raise ValueError('battery_reader_failed')
        response=json.loads(body)
        if not isinstance(response,dict) or set(response)!={'schema','id','hardware_hash','battery'} or type(response['schema']) is not int or response['schema']!=1 or response['id']!=source['id'] or response['hardware_hash']!=source['hardware_hash']: raise ValueError('battery_identity')
        value=validate(response['battery'])
        if value['status']!='ok' or not -60<=(dt.datetime.now(dt.timezone.utc)-instant(value['observed_at'])).total_seconds()<120: raise ValueError('battery_stale')
        return {**value,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError): return empty('unreachable',dt.datetime.now(dt.timezone.utc).isoformat())
    finally:
        if timer is not None:timer.cancel()
        kill()
        if process is not None:
            process.wait()
            if process.stdout is not None:process.stdout.close()

def collect(config_path=P('/etc/cpa-dashboard/mac-battery-sources.json'),cache_path=P('/var/lib/cpa-dashboard/mac-battery.json'),now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:
        raw=config_path.read_bytes()
        if len(raw)>32768:raise ValueError('battery_config_size')
        fingerprint=hashlib.sha256(raw).hexdigest();config=json.loads(raw)
        if set(config)!={'schema','sources'} or type(config['schema']) is not int or config['schema']!=1 or not isinstance(config['sources'],list) or len(config['sources'])>20:raise ValueError('battery_config')
        ids=set()
        for s in config['sources']:
            if set(s)!={'id','ssh_host','hardware_hash'} or not isinstance(s['id'],str) or not SLUG.fullmatch(s['id']) or s['id'] in ids:raise ValueError('battery_source')
            ids.add(s['id'])
            if s['ssh_host'] is not None and (not isinstance(s['ssh_host'],str) or not SLUG.fullmatch(s['ssh_host']) or not isinstance(s['hardware_hash'],str) or not re.fullmatch('[a-f0-9]{64}',s['hardware_hash'])):raise ValueError('battery_route')
        try:
            raw=cache_path.read_bytes()
            if len(raw)>131072:raise ValueError('battery_cache_size')
            cached=json.loads(raw);age=(now-instant(cached['attempted_at'])).total_seconds()
            if cached.get('source_fingerprint')==fingerprint and isinstance(cached.get('machines'),dict) and set(cached['machines'])==ids and -60<=age<INTERVAL:
                return {k:validate(v) for k,v in cached['machines'].items()}
        except (OSError,ValueError,TypeError,KeyError):pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            values=dict(zip([s['id'] for s in config['sources']],pool.map(lambda s:pull(s,now),config['sources'])))
        with tempfile.NamedTemporaryFile(dir=cache_path.parent,delete=False) as f:
            os.fchmod(f.fileno(),0o600);f.write(json.dumps({'attempted_at':now.isoformat(),'source_fingerprint':fingerprint,'machines':values},allow_nan=False).encode());f.flush();os.fsync(f.fileno())
        os.replace(f.name,cache_path)
        return values
    except (OSError,ValueError,TypeError,KeyError):return {}

if __name__=='__main__':local()
