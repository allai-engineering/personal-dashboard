"""Closed public schema; message bodies and model output are never public fields."""
import datetime as dt
import re
from urllib.parse import urlsplit


def validate(data):
    if not isinstance(data, dict) or set(data) != {'schema', 'checked_at', 'coverage', 'records'} or data['schema'] != 1:
        raise ValueError('mail_schema')
    def stamp(s):
        if not isinstance(s, str) or len(s) > 40 or dt.datetime.fromisoformat(s.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('mail_time')
    stamp(data['checked_at'])
    if not isinstance(data['coverage'], list) or len(data['coverage']) > 20:
        raise ValueError('mail_coverage')
    for c in data['coverage']:
        if set(c) != {'mailbox', 'status', 'checked_at', 'history_complete'} or not re.fullmatch('[a-z][a-z0-9-]{0,40}', c['mailbox']):
            raise ValueError('mail_coverage_fields')
        if c['status'] not in ('ok', 'partial', 'unavailable', 'login_required') or type(c['history_complete']) is not bool:
            raise ValueError('mail_status')
        stamp(c['checked_at'])
    if not isinstance(data['records'], list) or len(data['records']) > 500:
        raise ValueError('mail_records')
    ids = set()
    for r in data['records']:
        if set(r) != {'id', 'service', 'amount', 'currency', 'amount_kind', 'renewal_date', 'status', 'sources'}:
            raise ValueError('mail_fields')
        if not isinstance(r['id'], str) or not re.fullmatch('[a-f0-9]{32}', r['id']) or r['id'] in ids:
            raise ValueError('mail_id')
        ids.add(r['id'])
        if not isinstance(r['service'], str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,120})\.[a-z]{2,20}', r['service']):
            raise ValueError('mail_service')
        if r['amount'] is not None and (not isinstance(r['amount'], str) or not re.fullmatch(r'\d{1,9}(?:\.\d{1,2})?', r['amount'])):
            raise ValueError('mail_amount')
        if r['currency'] not in (None, 'USD', 'EUR', 'GBP', 'RUB', 'PLN', 'TRY', 'KZT', 'AED', 'INR') or (r['amount'] is None) != (r['currency'] is None):
            raise ValueError('mail_currency')
        if r['amount_kind'] not in ('last_payment', 'next_charge', 'invoice_due', 'unknown') or (r['amount'] is None and r['amount_kind'] != 'unknown'):
            raise ValueError('mail_amount_kind')
        if r['renewal_date'] is not None and (not isinstance(r['renewal_date'], str) or dt.date.fromisoformat(r['renewal_date']).isoformat() != r['renewal_date']):
            raise ValueError('mail_date')
        if r['status'] not in ('observed', 'cancelled', 'payment_failed') or not isinstance(r['sources'], list) or not 1 <= len(r['sources']) <= 5:
            raise ValueError('mail_evidence')
        for s in r['sources']:
            if set(s) != {'mailbox', 'ref', 'date', 'url', 'fields'} or not re.fullmatch('[a-z][a-z0-9-]{0,40}', s['mailbox']) or not re.fullmatch('[a-f0-9]{32}', s['ref']):
                raise ValueError('mail_source')
            if not isinstance(s['fields'], list) or len(s['fields']) > 3 or any(f not in ('amount', 'renewal', 'status') for f in s['fields']) or len(set(s['fields'])) != len(s['fields']):
                raise ValueError('mail_source_fields')
            stamp(s['date'])
            if s['url'] is not None:
                u = urlsplit(s['url'])
                if (u.scheme != 'https' or u.netloc != 'mail.google.com' or u.path != '/mail/' or not re.fullmatch(r'authuser=[A-Za-z0-9%._+@-]{3,260}', u.query)
                        or not re.fullmatch('all/[a-f0-9]{1,64}', u.fragment)):
                    raise ValueError('mail_source_url')
        for field, known in [('amount', r['amount'] is not None), ('renewal', r['renewal_date'] is not None), ('status', r['status'] != 'observed')]:
            if known and not any(field in s['fields'] for s in r['sources']):
                raise ValueError('mail_field_source')
    return data
