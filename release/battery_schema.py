"""Battery data contract; no collectors, SSH, or platform commands."""
import datetime as dt,re

FIELDS='status observed_at checked_at charge_percent health_percent health_condition cycle_count is_charging limit_status limit_percent limit_enabled'.split()
METRICS='charge_percent health_percent cycle_count is_charging limit_percent limit_enabled'.split()
def instant(value):
    if not isinstance(value,str) or len(value)>40: raise ValueError('battery_time')
    parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('battery_time')
    return parsed

def empty(status='unavailable',checked_at=None):
    return dict(status=status,observed_at=None,checked_at=checked_at,health_condition='unknown',limit_status='unavailable',**dict.fromkeys(METRICS))

def validate(value):
    if not isinstance(value,dict) or set(value)!=set(FIELDS): raise ValueError('battery_fields')
    if value['status'] not in ('ok','unreachable','not_connected','unavailable'): raise ValueError('battery_status')
    for key in ('observed_at','checked_at'):
        if value[key] is not None: instant(value[key])
    for key in ('charge_percent','health_percent','limit_percent','cycle_count'):
        x=value[key]
        if x is not None and (type(x) is not int or not 0<=x<=(100000 if key=='cycle_count' else 100)): raise ValueError('battery_number')
    for key in ('is_charging','limit_enabled'):
        if value[key] is not None and type(value[key]) is not bool: raise ValueError('battery_boolean')
    if value['health_condition'] not in ('normal','service_recommended','unknown'): raise ValueError('battery_health')
    if value['limit_status'] not in ('ok','unsupported','unavailable'): raise ValueError('battery_limit')
    if value['status']=='ok':
        if value['observed_at'] is None or value['checked_at'] is None: raise ValueError('battery_observation')
        if value['limit_status']=='ok':
            if value['limit_percent'] is None or value['limit_enabled'] is None: raise ValueError('battery_limit_missing')
        elif value['limit_percent'] is not None or value['limit_enabled'] is not None: raise ValueError('battery_limit_unknown')
    elif any(value[k] is not None for k in METRICS) or value['observed_at'] is not None or value['health_condition']!='unknown' or value['limit_status']!='unavailable':
        raise ValueError('failed_battery_metrics')
    return value

