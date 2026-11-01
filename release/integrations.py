import datetime as dt,math,re
SLUG=re.compile(r'[a-z][a-z0-9-]{0,47}')
def stamp(v):
 if not isinstance(v,str) or len(v)>40 or dt.datetime.fromisoformat(v.replace('Z','+00:00')).tzinfo is None:raise ValueError('timestamp')
def text(v,n):
 if not isinstance(v,str) or not 1<=len(v)<=n or any(ord(c)<32 for c in v):raise ValueError('text')
def records(rows):
 if not isinstance(rows,list) or len(rows)>100:raise ValueError('records')
 ids=set()
 for r in rows:
  required={'id','kind','title','state','observed_at'};optional={'value','unit','plan','weekly_remaining','five_hour_remaining','weekly_reset_at','five_hour_reset_at','detail'}
  if not isinstance(r,dict) or not required<=r.keys() or r.keys()-required-optional:raise ValueError('fields')
  if not isinstance(r['id'],str) or not SLUG.fullmatch(r['id']) or r['id'] in ids:raise ValueError('id')
  ids.add(r['id']);text(r['title'],100);stamp(r['observed_at'])
  if r['kind'] not in ('account','balance','service') or r['state'] not in ('ok','warning','critical','unknown','auth_required'):raise ValueError('state')
  for k in ('value','weekly_remaining','five_hour_remaining'):
   v=r.get(k)
   if v is not None:
    if type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e12:raise ValueError('number')
    if k!='value' and not 0<=v<=100:raise ValueError('percent')
    if r['state'] in ('unknown','auth_required'):raise ValueError('unknown_number')
  if r.get('unit') not in (None,'USD','EUR','RUB','credits','percent'):raise ValueError('unit')
  for k in ('weekly_reset_at','five_hour_reset_at'):
   if r.get(k) is not None:stamp(r[k])
  for k,n in (('plan',40),('detail',180)):
   if r.get(k) is not None:text(r[k],n)
 return rows

def validate_integrations(d):
 if not isinstance(d,dict) or set(d)!={'schema','collected_at','integrations'} or d['schema']!=1:raise ValueError('schema')
 stamp(d['collected_at'])
 if not isinstance(d['integrations'],list) or len(d['integrations'])>20:raise ValueError('integrations')
 ids=set()
 for x in d['integrations']:
  if set(x)!={'id','title','status','observed_at','revision','records'} or not SLUG.fullmatch(x['id']) or x['id'] in ids:raise ValueError('entry')
  ids.add(x['id']);text(x['title'],100);stamp(x['observed_at'])
  if x['status'] not in ('ok','unknown','auth_required') or not re.fullmatch('[a-f0-9]{64}',x['revision']):raise ValueError('status')
  records(x['records'])
 return d
