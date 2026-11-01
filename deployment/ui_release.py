#!/usr/bin/python3 -I
"""Fixed-repository, assets-only UI activation. No generic paths, commands or root code."""
import base64, datetime as dt, fcntl, hashlib, http.client, importlib.util, io, json, os
import pathlib, re, shutil, stat, subprocess, sys, tarfile, tempfile, time, urllib.parse, urllib.request
P=pathlib.Path
REPO='allai-engineering/personal-dashboard'
ROOT=P('/var/lib/dashboard-ui');CURRENT=P('/opt/cpa-dashboard/current')
POLICY=P('/etc/dashboard-ui/policy.json');MAX_BYTES=8*1024*1024
PROTECTED_WEB={'login.html','login.css','limits.mjs','model.mjs','sources.mjs','account-view.mjs','operations-view.mjs','integrations-view.mjs'}

def fail(code):raise ValueError(code)
def digest(body):return hashlib.sha256(body).hexdigest()
def sha(path):return digest(path.read_bytes())
def load(path):return json.loads(path.read_text())
def atomic(path,body,mode=0o640,gid=None):
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  os.fchmod(f.fileno(),mode)
  if gid is not None:os.fchown(f.fileno(),0,gid)
  f.write(body);f.flush();os.fsync(f.fileno())
 os.replace(f.name,path)

def validate_web(name):
 p=pathlib.PurePosixPath(name)
 if not isinstance(name,str) or not 1<=len(name)<=180 or p.is_absolute() or any(not re.fullmatch('[A-Za-z0-9_-][A-Za-z0-9_.-]*',v) or v in ('.','..') for v in p.parts):fail('asset_path')
 if p.parts[0]!='web' or p.suffix not in ('.html','.css','.mjs','.js','.png','.jpg','.jpeg','.webp'):fail('asset_type')
 if len(p.parts)==2 and p.name in PROTECTED_WEB:fail('protected_asset')
 return name

def unpack(body,policy):
 if len(body)>MAX_BYTES:fail('archive_size')
 files={};total=0
 with tarfile.open(fileobj=io.BytesIO(body),mode='r|gz') as tar:
  prefix=None;count=0
  for item in tar:
   count+=1
   if count>250:fail('file_count')
   parts=pathlib.PurePosixPath(item.name).parts
   if not parts or parts[0] in ('.','..') or item.name.startswith('/'):fail('archive_path')
   if prefix is None:prefix=parts[0]
   if prefix!=parts[0] or any(v in ('.','..') for v in parts):fail('archive_path')
   if item.isdir():continue
   if not item.isfile() or item.size>1024*1024:fail('archive_entry')
   total+=item.size
   if total>MAX_BYTES:fail('archive_size')
   name='/'.join(parts[1:])
   if name in files:fail('duplicate_file')
   files[name]=tar.extractfile(item).read()
 for name,expected in policy['trusted_hashes'].items():
  if name not in files or digest(files[name])!=expected:fail('protected_source_changed')
 assets={}
 for name,body in files.items():
  if not name.startswith('release/web/'):continue
  relative=name[len('release/'):]
  if relative in {'web/'+n for n in PROTECTED_WEB}:continue
  validate_web(relative);assets[relative]=body
 if 'web/index.html' not in assets or not 1<=len(assets)<=100:fail('asset_count')
 return assets

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def fetch(url,limit=MAX_BYTES):
 # Only these exact HTTPS origins; no credentials or caller-provided URL.
 allowed={'api.github.com','codeload.github.com'}
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
 for _ in range(2):
  parsed=urllib.parse.urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port not in (None,443):fail('github_origin')
  try:
   with opener.open(urllib.request.Request(url,headers={'User-Agent':'dashboard-ui-release','Accept':'application/vnd.github+json'}),timeout=20) as r:body=r.read(limit+1)
  except urllib.error.HTTPError as e:
   if e.code in (301,302,307) and e.headers.get('Location'):url=urllib.parse.urljoin(url,e.headers['Location']);continue
   fail('github_read_failed')
  if len(body)>limit:fail('github_body_limit')
  return body
 fail('github_redirect')
def api(suffix):return json.loads(fetch('https://api.github.com/repos/'+REPO+suffix,1024*1024))
def candidate(commit,policy):
 if not isinstance(commit,str) or not re.fullmatch('[a-f0-9]{40}',commit):fail('commit')
 head=api('/commits/main')
 if head.get('sha')!=commit:fail('stale_main_commit')
 runs=api('/actions/runs?head_sha='+commit+'&event=push&per_page=30').get('workflow_runs',[])
 valid=[r for r in runs if r.get('head_sha')==commit and r.get('head_branch')=='main' and r.get('event')=='push' and r.get('path')=='.github/workflows/ci.yml' and r.get('status')=='completed' and r.get('conclusion')=='success' and r.get('repository',{}).get('full_name')==REPO]
 if not valid:fail('ci_not_green')
 assets=unpack(fetch('https://api.github.com/repos/'+REPO+'/tarball/'+commit),policy)
 return assets,max(r['id'] for r in valid)

def identity(unit):
 value=dict(l.split('=',1) for l in subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','NRestarts','-p','ExecMainStartTimestampMonotonic'],text=True,timeout=5).splitlines())
 return value

def protected(policy):
 return {'files':{n:sha(P(n)) for n in policy['runtime_files']},'processes':{u:identity(u) for u in ('cliproxyapi','cpa-usage-keeper','hermes-gateway','cpa-dashboard-ingress')}}
def verify_current(old,policy):
 for n,expected in policy['trusted_hashes'].items():
  if n.startswith('release/'):
   relative=n[len('release/'):]
   if sha(old/relative)!=expected:fail('installed_baseline_drift')
 if not old.is_relative_to(CURRENT.parent/'releases') or old.is_symlink():fail('current_release')

def request(path,cookie=None):
 c=http.client.HTTPConnection('127.0.0.1',8766,timeout=5)
 try:
  c.request('GET',path,headers={'Cookie':cookie} if cookie else {});r=c.getresponse();return r.status,dict(r.getheaders()),r.read(MAX_BYTES+1)
 finally:c.close()
def session(old):
 spec=importlib.util.spec_from_file_location('ui_dashboard',old/'server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 auth=m.load_auth(P('/etc/cpa-dashboard/http-auth.json'))
 if not isinstance(auth,m.PasswordAuth) or m.SESSION_SECONDS!=30*86400:fail('auth_contract')
 return auth.cookie().split(';',1)[0]
def restart():subprocess.run(['systemctl','restart','cpa-dashboard.service'],check=True,capture_output=True,timeout=25)
def switch(target):
 link=CURRENT.parent/'.ui-current'
 if link.exists() or link.is_symlink():fail('release_link_busy')
 link.symlink_to(target);os.replace(link,CURRENT)
def health(cookie,assets):
 ready=False
 for _ in range(25):
  try:
   status,_,body=request('/');ready=status==200 and b'name="password"' in body and b'name="username"' not in body
  except OSError:pass
  if ready:break
  time.sleep(.2)
 if not ready:fail('login_not_ready')
 if request('/api/snapshot')[0]!=401 or request('/accounts.mjs')[0]!=401:fail('auth_gate')
 status,_,body=request('/api/snapshot',cookie)
 if status!=200:fail('session_not_preserved')
 data=json.loads(body)
 if data.get('read_only') is not True or data.get('generation_requests_sent')!=0:fail('read_only_contract')
 for name,expected in assets.items():
  status,headers,body=request('/' if name=='web/index.html' else '/'+name[4:],cookie)
  if status!=200 or digest(body)!=digest(expected):fail('served_asset_mismatch')
  csp=headers.get('Content-Security-Policy','')
  if "connect-src 'self'" not in csp or "form-action 'self'" not in csp:fail('security_headers')

def activate(old,new,cookie,assets,guard,check_guard):
 switched=False
 try:
  if CURRENT.resolve()!=old:fail('concurrent_deployment')
  switch(new);switched=True;restart();health(cookie,assets)
  if check_guard()!=guard:fail('protected_runtime_changed')
 except Exception:
  if switched and CURRENT.resolve()==new:
   switch(old);restart();health(cookie,{})
  raise

def apply(payload,policy):
 if set(payload)!={'sha','expected_current','review'}:fail('apply_fields')
 old=CURRENT.resolve(strict=True)
 if payload['expected_current']!=str(old):fail('stale_current')
 review=payload['review']
 if not isinstance(review,str) or not 20<=len(review)<=1000 or any(ord(c)<32 for c in review):fail('visual_review_required')
 verify_current(old,policy);assets,run_id=candidate(payload['sha'],policy)
 cookie=session(old);health(cookie,{})
 # A fully checked unchanged commit does not restart a live service.
 protected_names={'web/'+n for n in PROTECTED_WEB}
 installed={str(p.relative_to(old)) for p in (old/'web').rglob('*') if p.is_file() and str(p.relative_to(old)) not in protected_names}
 if installed==set(assets) and all((old/n).is_file() and sha(old/n)==digest(b) for n,b in assets.items()):return {'unchanged':True,'commit':payload['sha'],'ci_run':run_id,'auth_verified':True}
 guard=protected(policy);new=old.parent/('ui-'+payload['sha'])
 if new.exists():fail('release_exists')
 shutil.copytree(old,new,ignore=shutil.ignore_patterns('__pycache__'))
 gid=(old/'server.py').stat().st_gid
 for name in installed-set(assets):(new/name).unlink()
 for p in [new,*new.rglob('*')]:
  if p.is_symlink():fail('release_symlink')
  os.chown(p,0,gid);p.chmod(0o750 if p.is_dir() else 0o640)
 for name,body in assets.items():
  p=new/name;p.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
  for directory in [p.parent,*p.parent.parents]:
   if directory==new:break
   os.chown(directory,0,gid);directory.chmod(0o750)
  atomic(p,body,gid=gid)
 # Verify filesystem access in the actual service identity before the switch.
 r=subprocess.run(['/usr/sbin/runuser','-u','cpa-dashboard','--','/usr/bin/python3','-I','-c',"import pathlib,sys;r=pathlib.Path(sys.argv[1]);assert (r/'server.py').read_bytes();assert (r/'web/index.html').read_bytes()",str(new)],capture_output=True,timeout=10)
 if r.returncode:fail('service_user_permissions')
 activate(old,new,cookie,assets,guard,lambda:protected(policy))
 receipt={'commit':payload['sha'],'ci_run':run_id,'release':str(new),'previous':str(old),'review':review,'applied_at':dt.datetime.now(dt.timezone.utc).isoformat(),'protected_unchanged':True}
 atomic(ROOT/'latest.json',json.dumps(receipt).encode());return receipt

def rollback(payload,policy):
 if set(payload)!={'expected_current'}:fail('rollback_fields')
 receipt=load(ROOT/'latest.json');old=CURRENT.resolve(strict=True)
 if payload['expected_current']!=str(old) or str(old)!=receipt['release']:fail('stale_current')
 target=P(receipt['previous']).resolve(strict=True);verify_current(target,policy)
 cookie=session(old);guard=protected(policy)
 activate(old,target,cookie,{},guard,lambda:protected(policy))
 atomic(ROOT/'latest.json',json.dumps({'release':str(target),'previous':str(old),'rolled_back':True,'applied_at':dt.datetime.now(dt.timezone.utc).isoformat()}).encode())
 return {'restored':str(target),'protected_unchanged':True}

def main():
 if os.geteuid()!=0 or len(sys.argv)!=2 or sys.argv[1] not in ('status','check','apply','rollback'):fail('fixed_action')
 ROOT.mkdir(exist_ok=True,mode=0o700)
 with (ROOT/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  policy=load(POLICY);action=sys.argv[1]
  if action=='status':result={'repo':REPO,'current':str(CURRENT.resolve()),'latest':load(ROOT/'latest.json') if (ROOT/'latest.json').exists() else None,'protected_web':sorted(PROTECTED_WEB)}
  else:
   raw=sys.stdin.buffer.read(16385)
   if len(raw)>16384:fail('payload_size')
   payload=json.loads(raw)
   if action=='check':
    if set(payload)!={'sha'}:fail('check_fields')
    assets,run=candidate(payload['sha'],policy);verify_current(CURRENT.resolve(strict=True),policy)
    result={'checked':True,'commit':payload['sha'],'ci_run':run,'asset_count':len(assets),'sha256':{n:digest(b) for n,b in assets.items()}}
   elif action=='apply':result=apply(payload,policy)
   else:result=rollback(payload,policy)
  print(json.dumps(result,sort_keys=True))
if __name__=='__main__':
 try:main()
 except Exception as e:
  # Never emit HTTP bodies, snapshot data, credentials or arbitrary exception text.
  code=str(e) if isinstance(e,ValueError) and re.fullmatch('[a-z_]{1,60}',str(e)) else type(e).__name__
  print(json.dumps({'error':code}));raise SystemExit(1)
