"""Allowlisted dashboard data. No upstream bodies, credentials or host addresses."""
import datetime as dt
import math
import re

SCHEMA = 'personal-dashboard-operations-v1'
PROVIDERS = {'openrouter': ('OpenRouter', 'USD'), 'kie': ('Kie', 'credits'), 'digitalocean': ('DigitalOcean', 'USD')}
STATUSES = {'ok', 'unavailable', 'auth_error', 'rate_limited', 'not_configured', 'invalid_data'}
SEVERITIES = {'critical', 'warning', 'unknown'}
KINDS = {'physical', 'virtual_machine', 'cloud_vm', 'physical_mac', 'wsl_guest', 'managed_kubernetes_node', 'physical_router', 'services', 'unknown'}

def number(value, minimum=None, maximum=None, decimal_string=False):
    if decimal_string and isinstance(value, str) and re.fullmatch(r'-?\d{1,15}(?:\.\d{1,12})?', value):
        value = float(value)
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e15:
        raise ValueError('invalid_number')
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError('invalid_number')
    return value

def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('invalid_time')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('invalid_time')
    return parsed

def fresh(value, now, ttl):
    try:
        return -60 <= (now - timestamp(value)).total_seconds() < ttl
    except (ValueError, TypeError, OverflowError):
        return False

def exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError('unexpected_fields')

def text(value, limit=160):
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError('invalid_text')

def balance(provider, payload, now):
    title, unit = PROVIDERS[provider]
    result = {'id': provider, 'title': title, 'unit': unit, 'status': 'ok', 'observed_at': now.isoformat(),
              'source_at': now.isoformat(), 'remaining': None, 'month_spend': None, 'accrued_due': None}
    if provider == 'openrouter':
        data = payload['data']
        result['remaining'] = number(data['total_credits'], 0) - number(data['total_usage'], 0)
    elif provider == 'kie':
        if type(payload.get('code')) is not int or payload['code'] != 200:
            raise ValueError('provider_rejected')
        result['remaining'] = number(payload['data'], 0)
    else:
        # DO's signed balance includes current-month charges; a negative value is credit.
        signed = number(payload['month_to_date_balance'], decimal_string=True)
        account = number(payload['account_balance'], decimal_string=True)
        spent = number(payload['month_to_date_usage'], 0, decimal_string=True)
        if abs(signed - account - spent) > .011:
            raise ValueError('inconsistent_balance')
        timestamp(payload['generated_at'])
        result.update(source_at=payload['generated_at'], remaining=max(0, -signed),
                      accrued_due=max(0, signed), month_spend=spent)
    return result

def unavailable_balance(provider, status, now):
    title, unit = PROVIDERS[provider]
    return {'id': provider, 'title': title, 'unit': unit, 'status': status,
            'observed_at': now.isoformat(), 'source_at': None, 'remaining': None, 'month_spend': None, 'accrued_due': None}

def issue(raw, observed_at, category):
    check, severity = raw.get('check'), raw.get('severity')
    if not isinstance(check, str) or severity not in SEVERITIES:
        raise ValueError('invalid_issue')
    if check.startswith('disk:'):
        code, message = 'disk', 'Мало места на диске'
    elif check.startswith('failed:'):
        code, message = 'service', 'Есть службы с ошибкой'
    elif check.startswith('backup:'):
        code, message = 'backup', 'Проблема резервного копирования'
    elif check.startswith('kuma:'):
        code, message = 'application', 'Проверка приложения или бэкапа требует внимания'
    elif check == 'connection':
        code, message = 'connection', 'Нет связи с диагностикой'
    elif check == 'coverage':
        code, message = 'coverage', 'Диагностика не подключена'
    else:
        code, message = 'other', 'Проверка Hermes требует внимания'
    return {'code': code, 'text': message, 'severity': severity, 'category': category,
            'observed_at': observed_at, 'ttl_seconds': 25200 if category == 'host' else 900}

def validate_aliases(machines):
    used = {m['id'] for m in machines}
    for m in machines:
        names = m.get('aliases', [])
        if not isinstance(names, list) or len(names) > 10: raise ValueError('machine_aliases')
        for name in names:
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', name) or name in used:
                raise ValueError('machine_aliases')
            used.add(name)

def fleet(inventory, latest, current, now):
    if inventory.get('schema') != 1 or latest.get('schema') != 1 or current.get('schema') != 1:
        raise ValueError('fleet_schema')
    entries, probes = inventory['machines'], latest['machines']
    if not isinstance(entries, list) or not isinstance(probes, list) or len(entries) > 200 or len(probes) > 200:
        raise ValueError('fleet_size')
    validate_aliases(entries)
    lookup = {m['id']: m for m in probes}
    if len(lookup) != len(probes):
        raise ValueError('duplicate_machine')
    latest_time = latest['observed_at']; timestamp(latest_time)
    current_time = current['observed_at']; timestamp(current_time)
    records = []
    for entry in entries:
        mid = entry['id']
        if not isinstance(mid, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', mid):
            raise ValueError('invalid_machine_id')
        m = lookup.get(mid, {})
        probe = m.get('probe') or {}; checks = probe.get('checks') or {}
        observed = probe.get('observed_at') or latest_time
        state = m.get('state')
        state = state if state in ('observed_ok', 'degraded', 'unreachable', 'not_enrolled') else 'unknown'
        issues = [issue(x, observed, 'host') for x in m.get('issues', [])]
        unique = {(x['code'], x['severity']): x for x in issues}
        metrics = {'disk_free_percent': None, 'memory_available_percent': None, 'load1': None, 'cpu_count': None}
        disks = []
        for key, value in checks.items():
            if key.startswith('disk:') and isinstance(value, dict):
                try: disks.append(number(value.get('free_percent'), 0, 100))
                except ValueError: pass
        if disks: metrics['disk_free_percent'] = min(disks)
        memory = checks.get('memory', {})
        try:
            # Linux MemAvailable includes reclaimable memory; macOS free memory is not equivalent.
            available, total = number(memory.get('MemAvailable'), 0), number(memory.get('MemTotal'), 1)
            metrics['memory_available_percent'] = number(round(available / total * 100, 1), 0, 100)
        except ValueError: pass
        try: metrics['load1'] = number((probe.get('load') or [None])[0], 0)
        except ValueError: pass
        try: metrics['cpu_count'] = number(probe.get('cpu_count'), 1, 100000)
        except ValueError: pass
        records.append({'id': mid, 'kind': entry.get('kind') if entry.get('kind') in KINDS else 'unknown',
                        'state': state, 'observed_at': observed, 'metrics': metrics, 'issues': list(unique.values())})
        if entry.get('aliases'): records[-1]['aliases'] = list(entry['aliases'])
    lookup = {m['id']: m for m in records}
    if len(lookup) != len(records): raise ValueError('duplicate_inventory')
    for raw in current.get('summary', {}).get('issues', []):
        check = raw.get('check', '')
        if not isinstance(check, str) or not (check.startswith('backup:') or check.startswith('kuma:')): continue
        category = 'backup' if check.startswith('backup:') else 'monitor'
        observed = (current.get('backup_evidence') or {}).get('observed_at') if category == 'backup' else current.get('monitor_observed_at')
        mid = raw.get('machine')
        if mid not in lookup:
            if mid != 'applications': continue
            lookup[mid] = {'id': mid, 'kind': 'services', 'state': 'unknown', 'observed_at': observed,
                           'metrics': dict.fromkeys(['disk_free_percent','memory_available_percent','load1','cpu_count']), 'issues': []}
            records.append(lookup[mid])
        item = issue(raw, observed, category)
        # A missing timestamp stays explicitly unknown rather than inheriting receipt time.
        if observed is None: item['severity'] = 'unknown'
        lookup[mid]['issues'].append(item)
    return {'status': 'ok', 'observed_at': latest_time, 'inventory_count': len(entries),
            'enrolled': sum(e.get('enabled') is True for e in entries), 'machines': records}

def validate(value):
    exact(value, 'schema collected_at read_only balances fleet')
    if value['schema'] != SCHEMA or value['read_only'] is not True: raise ValueError('schema')
    timestamp(value['collected_at'])
    if not isinstance(value['balances'], list) or len(value['balances']) != 3: raise ValueError('balances')
    if {b.get('id') for b in value['balances']} != set(PROVIDERS): raise ValueError('providers')
    for b in value['balances']:
        exact(b, 'id title unit status observed_at source_at remaining month_spend accrued_due')
        if (b['title'],b['unit']) != PROVIDERS[b['id']] or b['status'] not in STATUSES: raise ValueError('balance')
        timestamp(b['observed_at'])
        if b['source_at'] is not None: timestamp(b['source_at'])
        for k in ('remaining', 'month_spend', 'accrued_due'):
            if b[k] is not None: number(b[k])
        if b['status'] != 'ok' and any(b[k] is not None for k in ('source_at','remaining','month_spend','accrued_due')): raise ValueError('failed_balance')
        if b['status'] == 'ok' and (b['source_at'] is None or b['remaining'] is None): raise ValueError('missing_balance')
    f = value['fleet']; exact(f, 'status observed_at inventory_count enrolled machines')
    if f['status'] not in ('ok','unavailable') or not isinstance(f['machines'],list) or len(f['machines']) > 201: raise ValueError('fleet')
    if f['observed_at'] is not None: timestamp(f['observed_at'])
    for k in ('inventory_count','enrolled'):
        if f[k] is not None: number(f[k],0,200)
    ids = set()
    for m in f['machines']:
        exact(m, 'id kind state observed_at metrics issues' + (' aliases' if 'aliases' in m else ''))
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',m['id']) or m['id'] in ids: raise ValueError('machine')
        ids.add(m['id'])
        if m['kind'] not in KINDS or m['state'] not in ('observed_ok','degraded','unreachable','not_enrolled','unknown'): raise ValueError('state')
        if m['observed_at'] is not None: timestamp(m['observed_at'])
        exact(m['metrics'],'disk_free_percent memory_available_percent load1 cpu_count')
        for k,v in m['metrics'].items():
            if v is not None: number(v,0,100 if k.endswith('percent') else 100000)
        if not isinstance(m['issues'],list) or len(m['issues'])>100: raise ValueError('issues')
        for i in m['issues']:
            exact(i, 'code text severity category observed_at ttl_seconds');text(i['text'])
            if i['code'] not in ('disk','service','backup','application','connection','coverage','other') or i['severity'] not in SEVERITIES or i['category'] not in ('host','backup','monitor'): raise ValueError('issue')
            if i['ttl_seconds'] != (25200 if i['category']=='host' else 900): raise ValueError('ttl')
            if i['observed_at'] is not None: timestamp(i['observed_at'])
    validate_aliases(f['machines'])
    return value
