"""Allowlisted Court/execution observations; no prompts, documents or operational actions."""
import datetime as dt
import re
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('cockpit_operations', Path(__file__).resolve().with_name('operations.py'))
_ops = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ops)
exact, number, text, timestamp = _ops.exact, _ops.number, _ops.text, _ops.timestamp

SCHEMA = 'captain-cockpit-v1'
PROFILES = {'default', 'ops', 'dashboard-dev', 'lawyer', 'monitor', 'research'}


def optional_time(value):
    if value is not None:
        timestamp(value)


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('invalid_cockpit_id')


def validate(value, now=None):
    exact(value, 'schema collected_at read_only court tasks profiles events' + (' work' if 'work' in value else ''))
    if 'work' in value:
        spec=importlib.util.spec_from_file_location('cockpit_incidents',Path(__file__).with_name('incident_schema.py'))
        contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
        contract.validate(value['work'])
    if value['schema'] != SCHEMA or value['read_only'] is not True:
        raise ValueError('cockpit_schema')
    collected = timestamp(value['collected_at'])
    if collected > (now or dt.datetime.now(dt.timezone.utc)) + dt.timedelta(seconds=60):
        raise ValueError('cockpit_future')
    c = value['court']
    exact(c, 'status observed_at receipt_status receipt_scope receipt_observed_at changes important unverified carried_forward search_status confirmed_dates_available known_cases')
    if c['status'] not in ('ok', 'partial', 'error', 'unavailable') or c['receipt_status'] not in ('ok', 'partial', 'error', 'unavailable'):
        raise ValueError('court_status')
    if c['receipt_scope'] not in ('courts', 'kad', 'kad_metadata', 'unknown') or c['search_status'] not in ('complete', 'incomplete', 'unknown') or type(c['confirmed_dates_available']) is not bool:
        raise ValueError('court_scope')
    optional_time(c['observed_at']); optional_time(c['receipt_observed_at'])
    if any(c[k] is not None and timestamp(c[k]) > collected + dt.timedelta(seconds=60)
           for k in ('observed_at', 'receipt_observed_at')):
        raise ValueError('court_future')
    for key in ('changes', 'important', 'unverified', 'carried_forward', 'known_cases'):
        if c[key] is not None:
            if type(c[key]) is not int:
                raise ValueError('court_count')
            number(c[key], 0, 100000)
    if c['status'] == 'ok' and (c['unverified'] != 0 or c['carried_forward'] != 0
            or c['search_status'] != 'complete' or c['receipt_status'] != 'ok'
            or c['receipt_scope'] != 'courts' or c['observed_at'] is None):
        raise ValueError('court_inconsistent_coverage')
    if not isinstance(value['profiles'], list) or len(value['profiles']) > len(PROFILES):
        raise ValueError('profile_count')
    seen = set()
    for p in value['profiles']:
        exact(p, 'id status stored_jobs')
        if p['id'] not in PROFILES or p['id'] in seen or p['status'] not in ('ok', 'partial', 'empty', 'unavailable'):
            raise ValueError('profile')
        seen.add(p['id'])
        if p['stored_jobs'] is not None and (type(p['stored_jobs']) is not int or not 0 <= p['stored_jobs'] <= 10000):
            raise ValueError('profile_jobs')
    if not isinstance(value['tasks'], list) or len(value['tasks']) > 100:
        raise ValueError('task_count')
    seen = set()
    for t in value['tasks']:
        exact(t, 'id job_key profile label state origin claimed_at started_at finished_at progress_at observed_at liveness next_run_at has_error enabled')
        ident(t['id']); ident(t['job_key']); text(t['label'], 160)
        if t['id'] in seen or t['profile'] not in PROFILES or t['state'] not in ('claimed', 'running', 'completed', 'failed', 'unknown', 'planned', 'paused'):
            raise ValueError('task_state')
        seen.add(t['id'])
        if t['origin'] not in ('scheduled', 'manual', 'unknown') or t['liveness'] not in ('verified', 'unverified', 'not_live', 'not_applicable') or type(t['has_error']) is not bool:
            raise ValueError('task_evidence')
        if t['enabled'] is not None and type(t['enabled']) is not bool:
            raise ValueError('task_enabled')
        if t['liveness'] == 'verified' and t['state'] not in ('claimed', 'running'):
            raise ValueError('task_liveness')
        for key in ('claimed_at', 'started_at', 'finished_at', 'progress_at', 'observed_at', 'next_run_at'):
            optional_time(t[key])
        if t['observed_at'] is None:
            raise ValueError('task_observation')
        if any(t[k] is not None and timestamp(t[k]) > collected + dt.timedelta(seconds=60)
               for k in ('claimed_at', 'started_at', 'finished_at', 'progress_at', 'observed_at')):
            raise ValueError('task_future')
    if not isinstance(value['events'], list) or len(value['events']) > 100:
        raise ValueError('event_count')
    seen = set()
    for e in value['events']:
        exact(e, 'id title at date_kind confirmed observed_at source')
        ident(e['id']); text(e['title'], 200); text(e['source'], 100)
        if e['id'] in seen or e['date_kind'] not in ('hearing', 'confirmed_deadline', 'inferred', 'publication') or type(e['confirmed']) is not bool:
            raise ValueError('event_kind')
        seen.add(e['id'])
        if e['date_kind'] == 'inferred' and e['confirmed']:
            raise ValueError('inferred_not_confirmed')
        if isinstance(e['at'], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', e['at']):
            dt.date.fromisoformat(e['at'])
        else:
            timestamp(e['at'])
        if timestamp(e['observed_at']) > collected + dt.timedelta(seconds=60):
            raise ValueError('event_future_observation')
    return value
