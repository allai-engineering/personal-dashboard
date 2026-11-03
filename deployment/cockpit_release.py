"""Owner-only core integration upgrade. No sudo grant or exception for the UI broker."""
import base64
import datetime as dt
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import pwd
import subprocess
import sys
import tarfile

_spec=importlib.util.spec_from_file_location('cockpit_ui_release',Path(__file__).resolve().with_name('ui_release.py'))
ui=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(ui)
DATA=Path('/var/lib/cpa-dashboard/cockpit');STATE=Path('/var/lib/dashboard-ui/core-upgrades')
FILES={'sources':Path('/etc/cpa-dashboard/cockpit-sources.json'),
       'dashboard':Path('/etc/systemd/system/cpa-dashboard.service.d/30-cockpit.conf'),
       'publisher':Path('/etc/systemd/system/dashboard-cockpit.service'),
       'launcher':Path('/usr/local/libexec/dashboard-cockpit-launch'),
       'timer':Path('/etc/systemd/system/dashboard-cockpit.timer'),
       'latest':Path('/var/lib/dashboard-ui/latest.json')}


def command(args,timeout=45):
    return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=timeout)


def source(commit):
    if not isinstance(commit,str) or not re.fullmatch('[a-f0-9]{40}',commit):ui.fail('commit')
    if ui.api('/commits/main').get('sha')!=commit:ui.fail('stale_main_commit')
    runs=ui.api('/actions/runs?head_sha='+commit+'&event=push&per_page=30').get('workflow_runs',[])
    valid=[r for r in runs if r.get('head_sha')==commit and r.get('head_branch')=='main' and r.get('event')=='push' and r.get('path')=='.github/workflows/ci.yml' and r.get('status')=='completed' and r.get('conclusion')=='success' and r.get('repository',{}).get('full_name')==ui.REPO]
    if not valid:ui.fail('ci_not_green')
    files={};size=0;prefix=None;entries=0
    with tarfile.open(fileobj=io.BytesIO(ui.fetch('https://api.github.com/repos/'+ui.REPO+'/tarball/'+commit)),mode='r|gz') as archive:
        for entry in archive:
            entries+=1;parts=Path(entry.name).parts
            if entries>250 or not parts or entry.name.startswith('/') or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',p) or p in ('.','..') for p in parts):ui.fail('archive_path')
            if prefix is None:prefix=parts[0]
            if parts[0]!=prefix:ui.fail('archive_prefix')
            if entry.isdir():continue
            if not entry.isfile() or entry.size>1024*1024:ui.fail('archive_entry')
            size+=entry.size
            if size>ui.MAX_BYTES:ui.fail('archive_size')
            name='/'.join(parts[1:])
            if name in files:ui.fail('archive_duplicate')
            files[name]=archive.extractfile(entry).read()
    return files,max(r['id'] for r in valid)


def baseline(files,old):
    value={**old,'trusted_hashes':{n:ui.digest(b) for n,b in files.items()
        if not n.startswith('release/web/') or n[len('release/web/'):] in ui.PROTECTED_WEB or n=='release/web/cockpit-view.mjs'}}
    value['runtime_files']=list(dict.fromkeys(old['runtime_files']+[str(p) for k,p in FILES.items() if k!='latest']))
    return value


def guard(policy):
    value=ui.protected(policy);units={}
    for name in ('cpa-dashboard-collect','personal-dashboard-collect','personal-dashboard-operations','dashboard-integrations'):
        for kind in ('service','timer'):
            text=command(['systemctl','show',name+'.'+kind,'-p','FragmentPath','-p','DropInPaths'])
            for line in text.splitlines():
                for path in line.partition('=')[2].split():
                    units[path]=ui.sha(Path(path))
    value['existing_collector_units']=units
    return value


def restore(files):
    errors=[]
    for path,item in files.items():
        try:
            if item is None:path.unlink(missing_ok=True)
            else:ui.atomic(path,item['body'],mode=item['mode'],gid=item['gid'])
        except OSError:errors.append('file_restore_failed')
    return errors


def verify_sidecar():
    spec=importlib.util.spec_from_file_location('release_cockpit',ui.CURRENT.resolve()/'cockpit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    value=module.validate(json.loads((DATA/'cockpit.json').read_text()))
    age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(value['collected_at'])).total_seconds()
    if not 0<=age<120 or value['court']['status']=='unavailable' or any(p['status']=='unavailable' for p in value['profiles']):ui.fail('sidecar_not_ready')


def apply(payload):
    if set(payload)!={'sha','expected_current','expected_policy_sha256','sources'}:ui.fail('fields')
    old=ui.CURRENT.resolve(strict=True);policy=ui.load(ui.POLICY)
    if str(old)!=payload['expected_current'] or ui.sha(ui.POLICY)!=payload['expected_policy_sha256']:ui.fail('stale_baseline')
    sources=payload['sources']
    if not isinstance(sources,dict) or set(sources)!={'hermes_home','court_alias','court_root'}:ui.fail('sources')
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,80}',sources['court_alias']):ui.fail('source_alias')
    if any(not isinstance(sources[k],str) or not sources[k].startswith('/') or any(ord(c)<32 for c in sources[k]) for k in ('hermes_home','court_root')):ui.fail('source_path')
    ui.verify_current(old,policy);files,run=source(payload['sha'])
    for name in ui.PROTECTED_WEB:
        if files.get('release/web/'+name)!=(old/'web'/name).read_bytes():ui.fail('protected_view_changed')
    required={'release/server.py','release/operations.py','release/integrations.py','release/cockpit.py','release/cockpit_read.py','release/cockpit_publish.py','release/web/index.html','deployment/cockpit_launch.py'}
    if not required.issubset(files):ui.fail('missing_core_source')
    new=old.parent/('cockpit-'+payload['sha'])
    if new.exists():ui.fail('release_exists')
    if any(FILES[k].exists() for k in ('sources','dashboard','publisher','timer')):ui.fail('core_already_configured')
    cookie=ui.session(old);ui.health(cookie,{})
    before=guard(policy)
    start=command(['systemctl','show','cpa-dashboard.service','--value','-p','ExecStart'])
    match=re.search(r'argv\[\]=([^;]+);',start)
    if not match:ui.fail('dashboard_command')
    args=shlex.split(match[1])
    if args[:3]!=['/usr/bin/python3','-I','/opt/cpa-dashboard/current/server.py'] or '--snapshot-file' not in args or '--auth-file' not in args or '--cockpit-file' in args:ui.fail('dashboard_command')
    args+=['--cockpit-file',str(DATA/'cockpit.json')]
    gid=(old/'server.py').stat().st_gid
    account=pwd.getpwnam('hermes')
    new.mkdir(mode=0o750);os.chown(new,0,gid)
    for name,body in files.items():
        if not name.startswith('release/'):continue
        path=new/name[len('release/'):];path.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
        for directory in path.parents:
            if directory==new:break
            os.chown(directory,0,gid);directory.chmod(0o750)
        ui.atomic(path,body,gid=gid)
    changes=[*FILES.values(),ui.POLICY,DATA/'cockpit.json',DATA/'cockpit-cadence.json']
    saved={}
    for path in changes:
        if path.is_symlink():ui.fail('configuration_symlink')
        saved[path]={'body':path.read_bytes(),'mode':stat.S_IMODE(path.stat().st_mode),'gid':path.stat().st_gid} if path.exists() else None
    backup=STATE/(payload['sha']+'-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True,mode=0o700)
    ui.atomic(backup/'files.json',json.dumps({str(p):None if v is None else {**v,'body':base64.b64encode(v['body']).decode()} for p,v in saved.items()}).encode(),0o600)
    try:
        for path in FILES.values():path.parent.mkdir(parents=True,exist_ok=True)
        DATA.mkdir(parents=True,exist_ok=True,mode=0o750)
        os.chown(DATA,account.pw_uid,gid);DATA.chmod(0o750)
        ui.atomic(FILES['sources'],json.dumps(sources).encode(),0o640,gid=account.pw_gid)
        ui.atomic(FILES['dashboard'],('[Service]\nExecStart=\nExecStart='+shlex.join(args)+'\n').encode(),0o644)
        unit='[Unit]\nDescription=Read existing Court and Hermes evidence for Captain Cockpit\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=hermes\nGroup=hermes\nSupplementaryGroups=cpa-dashboard\nExecStart=/usr/bin/python3 -I -B '+str(FILES['launcher'])+'\nUMask=0077\nTimeoutStartSec=55\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=full\nProtectHome=true\nInaccessiblePaths=-/etc/cpa-dashboard/http-auth.json -/var/lib/cliproxyapi\nRestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX\n'
        ui.atomic(FILES['launcher'],files['deployment/cockpit_launch.py'],0o644)
        ui.atomic(FILES['publisher'],unit.encode(),0o644)
        ui.atomic(FILES['timer'],b'[Unit]\nDescription=Refresh local task status; external sources keep their 15-minute gate\n[Timer]\nOnBootSec=30s\nOnUnitInactiveSec=30s\nAccuracySec=1s\n[Install]\nWantedBy=timers.target\n',0o644)
        command(['systemd-analyze','verify',str(FILES['publisher']),str(FILES['timer'])])
        command(['systemctl','daemon-reload'])
        ui.switch(new)
        command(['systemctl','start','dashboard-cockpit.service'],timeout=60)
        ui.restart()
        assets={n[len('release/'):]:b for n,b in files.items() if n.startswith('release/web/')}
        ui.health(cookie,assets);verify_sidecar()
        if guard(policy)!=before:ui.fail('protected_runtime_changed')
        updated=baseline(files,policy)
        ui.atomic(ui.POLICY,json.dumps(updated).encode(),0o600)
        ui.verify_current(new,updated)
        command(['systemctl','enable','--now','dashboard-cockpit.timer'])
        if command(['systemctl','is-active','dashboard-cockpit.timer']).strip()!='active':ui.fail('timer_not_active')
        receipt={'commit':payload['sha'],'ci_run':run,'release':str(new),'previous':str(old),'backup':str(backup),
            'applied_at':dt.datetime.now(dt.timezone.utc).isoformat(),'protected_unchanged':True,'auth_session_preserved':True,'publisher_interval_seconds':30,'external_read_interval_seconds':900,'core_release':True}
        ui.atomic(FILES['latest'],json.dumps(receipt).encode(),0o600)
        ui.atomic(backup/'receipt.json',json.dumps(receipt).encode(),0o600)
        return receipt
    except Exception:
        errors=[]
        for args in (['systemctl','disable','--now','dashboard-cockpit.timer'],['systemctl','stop','dashboard-cockpit.service']):
            try:command(args,timeout=60)
            except Exception:errors.append('publisher_shutdown_failed')
        errors+=restore(saved)
        try:
            if ui.CURRENT.resolve()==new:ui.switch(old)
        except Exception:errors.append('release_restore_failed')
        try:
            command(['systemctl','daemon-reload']);ui.restart();ui.health(cookie,{})
        except Exception:errors.append('restored_health_failed')
        ui.atomic(backup/'rollback.json',json.dumps({'errors':errors,'previous':str(old)}).encode(),0o600)
        if errors:ui.fail('rollback_incomplete')
        raise


if __name__=='__main__':
    try:
        if os.geteuid()!=0 or len(sys.argv)!=1:ui.fail('owner_root_required')
        raw=sys.stdin.buffer.read(16385)
        if len(raw)>16384:ui.fail('payload_size')
        with (ui.ROOT/'lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            print(json.dumps(apply(json.loads(raw))))
    except Exception as error:
        code=str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z_]{1,60}',str(error)) else type(error).__name__
        print(json.dumps({'error':code}));raise SystemExit(1)
