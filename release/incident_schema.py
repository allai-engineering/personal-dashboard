"""Allowlisted incident work evidence; no prompts, commands or raw logs."""
import datetime as dt
import re

ACTIONS={'diagnose','check_access','inspect_disk','inspect_service','inspect_backup','prepare_fix','test_fix','verify_recovery','wait_supervisor','wait_reset','check_balance','check_job','check_source'}
BLOCKERS={'none','no_access','no_safe_procedure','active_work','awaiting_source','upstream','execution_failed','login_required','payment_required','owner_approval'}
OWNER_BLOCKERS={'login_required','payment_required','owner_approval'}
STATES={'queued','accepted','waiting','needs_user','resolved'}
FIELDS=set('record_id condition_key fingerprint source_state source_at queued_at updated_at state action blocker decision task_ref execution_key execution_state execution_liveness'.split())

def stamp(v):
 if not isinstance(v,str):raise ValueError('incident_timestamp')
 d=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('incident_timezone')
 return d

def text(v,limit):
 if not isinstance(v,str) or not v or len(v)>limit or any(ord(c)<32 for c in v):raise ValueError('incident_text')
 if re.search(r'(?i)(bearer\s|sk-[a-z0-9]{12}|-----BEGIN|https?://[^\s/@]+:[^\s/@]+@)',v):raise ValueError('incident_private_text')

def validate(value):
 if not isinstance(value,dict) or set(value)!={'status','observed_at','items'} or value['status'] not in ('ok','unavailable'):raise ValueError('incident_work')
 observed=stamp(value['observed_at'])
 if not isinstance(value['items'],list) or len(value['items'])>200:raise ValueError('incident_count')
 seen=set()
 for w in value['items']:
  if not isinstance(w,dict) or set(w)!=FIELDS:raise ValueError('incident_fields')
  text(w['record_id'],240);text(w['condition_key'],500)
  if w['record_id'] in seen or not re.fullmatch('[a-f0-9]{64}',w['fingerprint']):raise ValueError('incident_identity')
  seen.add(w['record_id'])
  if w['source_state'] not in ('open','unknown','clear') or w['state'] not in STATES or w['action'] not in ACTIONS or w['blocker'] not in BLOCKERS:raise ValueError('incident_state')
  for key in ('source_at','queued_at','updated_at'):
   if stamp(w[key])>observed+dt.timedelta(seconds=60):raise ValueError('incident_future')
  if w['decision'] is not None:text(w['decision'],400)
  if w['task_ref'] is not None:text(w['task_ref'],100)
  if w['execution_key'] is not None and not re.fullmatch('[a-f0-9]{24}',w['execution_key']):raise ValueError('incident_execution')
  if w['execution_state'] not in ('unknown','claimed','running','completed','failed') or w['execution_liveness'] not in ('verified','unverified','not_live','not_applicable'):raise ValueError('incident_execution')
  if w['state']=='needs_user' and (w['blocker'] not in OWNER_BLOCKERS or not w['decision']):raise ValueError('incident_decision')
  if w['state']!='needs_user' and (w['decision'] is not None or w['blocker'] in OWNER_BLOCKERS):raise ValueError('incident_decision')
  if w['state']=='resolved' and w['source_state']!='clear':raise ValueError('incident_recovery')
 return value
