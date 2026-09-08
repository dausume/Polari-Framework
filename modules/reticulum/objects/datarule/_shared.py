"""@module reticulum.objects.datarule._shared — what the datarule row classes share (constants, seeds, helpers); split from datarule_basis.py (sap-2c)."""
import json

QUARANTINE_REASON_VALUES = ('oversize', 'over-rate', 'type-mismatch',
                            'duplicate', 'no-rule')
_TYPE_CHECKS = {
    'str': lambda v: isinstance(v, str),
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'float': lambda v: isinstance(v, (int, float))
    and not isinstance(v, bool),
    'bool': lambda v: isinstance(v, bool),
    'dict': lambda v: isinstance(v, dict),
    'list': lambda v: isinstance(v, list),
}
def payload_matches_schema(payload, schema, allow_extra=False):
    """STRICT typing gate: every schema field present with the right
    type; unknown fields refuse unless the rule explicitly allows
    them. Returns (True, '') or (False, reason-naming-the-field)."""
    if not isinstance(payload, dict):
        return (False, 'payload is not an object')
    for field, type_name in schema.items():
        if field not in payload:
            return (False, 'missing field %r' % field)
        checker = _TYPE_CHECKS.get(type_name)
        if checker is None:
            return (False, 'rule declares unknown type %r for %r — '
                           'fix the rule' % (type_name, field))
        if not checker(payload[field]):
            return (False, 'field %r is not %s' % (field, type_name))
    if not allow_extra:
        extras = sorted(set(payload) - set(schema))
        if extras:
            return (False, 'unmatched fields %s — this app\'s schema '
                           'does not know them' % extras)
    return (True, '')
def evaluate_submission(rule, identity, payload, payload_bytes,
                        window_count, seen_dedupe_values, now_ms):
    """One submission against one rule. Caller supplies the history
    (window_count = this identity's accepted submissions in the
    current window; seen_dedupe_values = this identity's prior dedupe
    keys). Returns (accepted, finding) — finding is None on accept,
    else a quarantine-row-shaped dict with reason + evidence."""
    def caught(reason, evidence):
        return (False, {'reason': reason, 'identity': identity,
                        'evidence': evidence, 'atMs': now_ms})

    if not rule or not rule.get('enabled'):
        return caught('no-rule',
                      'no enabled AppDataRule for this app — mesh '
                      'submissions without a rule are refused, not '
                      'defaulted')
    max_bytes = rule.get('max_submission_bytes') or 0
    if max_bytes and payload_bytes > max_bytes:
        return caught('oversize',
                      'submission %d B exceeds the per-submission cap '
                      '%d B' % (payload_bytes, max_bytes))
    max_rate = rule.get('max_submissions_per_window') or 0
    if max_rate and window_count >= max_rate:
        return caught('over-rate',
                      'identity already made %d submissions this '
                      'window (cap %d per %ds)'
                      % (window_count, max_rate,
                         rule.get('window_seconds', 0)))
    schema = {}
    try:
        schema = json.loads(rule.get('schema_json') or '{}')
    except ValueError:
        return caught('type-mismatch',
                      'the rule\'s schema_json is unparseable — fix '
                      'the rule; nothing passes a broken gate')
    if schema:
        ok, why = payload_matches_schema(
            payload, schema, bool(rule.get('allow_extra_fields')))
        if not ok:
            return caught('type-mismatch', why)
    dedupe_field = rule.get('dedupe_field') or ''
    if dedupe_field:
        value = (payload or {}).get(dedupe_field)
        if value is None:
            return caught('type-mismatch',
                          'dedupe field %r missing from payload'
                          % dedupe_field)
        if value in (seen_dedupe_values or set()):
            return caught('duplicate',
                          'identity already submitted %s=%r — one '
                          'ballot per box (dedupe_field)'
                          % (dedupe_field, value))
    return (True, None)
