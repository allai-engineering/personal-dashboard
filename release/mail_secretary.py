"""Closed public projection of the mail secretary; no free-form model strings."""
import datetime as dt
import re

KINDS = ('renewal', 'payment_notice', 'invoice', 'reply_needed', 'access', 'waiting_reply', 'resolved_notice')
BLOCKERS = ('owner_decision', 'current_state_unverified', 'awaiting_reply', 'notice_reviewed', 'technical_review')
OPERATIONS = ('search', 'targeted_search', 'read', 'read_pdf', 'verify', 'case_recorded', 'irrelevant_verified', 'skill_read', 'tool_error', 'handoff_queued')
SERVICES = ('unknown', 'excalidraw', 'neon', 'github', 'google', 'yandex', 'hostkey', 'openai', 'anthropic')


def validate(data):
    def fields(value, names):
        if not isinstance(value, dict) or set(value) != set(names.split()):
            raise ValueError('mail_secretary_fields')
    def stamp(value):
        if not isinstance(value, str) or len(value) > 40 or dt.datetime.fromisoformat(value).tzinfo is None:
            raise ValueError('mail_secretary_time')
    def count(value):
        if type(value) is not int or not 0 <= value <= 100000:
            raise ValueError('mail_secretary_count')
    def opaque(value):
        if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value):
            raise ValueError('mail_secretary_id')
    fields(data, 'schema checked_at run_state stop_reason pending coverage cases operations case_counts omitted_cases')
    if data['schema'] != 1 or data['run_state'] not in ('running', 'idle', 'partial', 'failed'):
        raise ValueError('mail_secretary_state')
    if data['stop_reason'] not in ('running', 'batch_complete', 'backlog', 'source_unavailable', 'model_unavailable', 'budget', 'not_started'):
        raise ValueError('mail_secretary_stop')
    stamp(data['checked_at']); count(data['pending'])
    fields(data['case_counts'], 'needs_user waiting done')
    for number in data['case_counts'].values():
        count(number)
    count(data['omitted_cases'])
    fields(data['coverage'], 'ok partial unavailable scope')
    for key in ('ok', 'partial', 'unavailable'):
        count(data['coverage'][key])
    if data['coverage']['scope'] != 'bounded_inbox_and_targeted':
        raise ValueError('mail_secretary_scope')
    if not isinstance(data['cases'], list) or len(data['cases']) > 500:
        raise ValueError('mail_secretary_cases')
    seen = set()
    for row in data['cases']:
        fields(row, 'id service kind state deadline confidence blocker next_action owner observed_at updated_at last_operation sources')
        opaque(row['id'])
        if row['id'] in seen:
            raise ValueError('mail_secretary_duplicate')
        seen.add(row['id'])
        if row['service'] not in SERVICES or row['kind'] not in KINDS or row['state'] not in ('needs_user', 'waiting', 'done'):
            raise ValueError('mail_secretary_case_state')
        if row['confidence'] != 'supported_notice' or row['blocker'] not in BLOCKERS:
            raise ValueError('mail_secretary_evidence')
        if row['next_action'] not in ('review_notice', 'review_renewal', 'review_invoice', 'review_reply', 'review_access', 'check_latest', 'none', 'ops_review') or row['owner'] not in ('user', 'ops', 'mail-secretary'):
            raise ValueError('mail_secretary_action')
        if row['last_operation'] not in ('evidence_verified', 'handoff_queued'):
            raise ValueError('mail_secretary_operation')
        if row['deadline'] is not None and (not isinstance(row['deadline'], str) or dt.date.fromisoformat(row['deadline']).isoformat() != row['deadline']):
            raise ValueError('mail_secretary_deadline')
        stamp(row['observed_at']); stamp(row['updated_at'])
        if not isinstance(row['sources'], list) or not 1 <= len(row['sources']) <= 5:
            raise ValueError('mail_secretary_sources')
        for source in row['sources']:
            opaque(source)
    if sum(data['case_counts'].values()) != len(data['cases']) + data['omitted_cases']:
        raise ValueError('mail_secretary_projection_count')
    for state, number in data['case_counts'].items():
        if sum(row['state'] == state for row in data['cases']) > number:
            raise ValueError('mail_secretary_projection_state')
    if not isinstance(data['operations'], list) or len(data['operations']) > 100:
        raise ValueError('mail_secretary_operations')
    for operation in data['operations']:
        fields(operation, 'action ref outcome at')
        if operation['action'] not in OPERATIONS or operation['outcome'] not in ('ok', 'source_unavailable', 'evidence_uncertain'):
            raise ValueError('mail_secretary_operation')
        if operation['ref'] is not None:
            opaque(operation['ref'])
        stamp(operation['at'])
    return data
