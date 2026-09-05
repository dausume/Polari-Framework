"""
@module reticulum.datarule_basis

PER-APP DATA RULES (ret-1c, Dustin 2026-08-13): what one consumer
may SUBMIT to a mesh app, and what happens to submissions that lie.

  - per-identity size and rate caps ("only this much at one time"),
  - STRICT typing: a payload whose shape does not match the app's
    declared schema is invalid — unmatched fields are refused, not
    tolerated (tolerated garbage is how attacks start),
  - ballot-box protection: duplicate submissions per identity (per
    dedupe key) are caught,
  - and everything caught is QUARANTINED as a row, never silently
    dropped — caught garbage is EVIDENCE, and a flood of it is an
    attack signature the census can point at.

Pure functions over plain dicts; the relay daemon enforces, rows
record. Rejection never mutates anything — an mesh submission
that passes every rule still only ever becomes a PROPOSAL (ret-8).

@consumers reticulum.reticulum_api, the relay daemon (sidecar)
@see modules/reticulum/meshapp_basis.py (the tier this guards),
     plan §5n
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: Why a submission was quarantined. A vocabulary, so dashboards can
#: count attack shapes rather than parse prose.
QUARANTINE_REASON_VALUES = ('oversize', 'over-rate', 'type-mismatch',
                            'duplicate', 'no-rule')

#: Schema type names a rule may declare per field.
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


class AppDataRule(treeObject):
    """What one consumer may submit to one app, per unit time —
    the inbound admission policy of the mesh tier. No enabled
    rule = nothing accepted (refused, not defaulted)."""

    @treeObjectInit
    def __init__(self, name='', app_name='', relay_name='',
                 max_submission_bytes=2048,
                 max_submissions_per_window=10, window_seconds=3600,
                 schema_json='{}', allow_extra_fields=False,
                 dedupe_field='', enabled=False, notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.relay_name = relay_name
        self.max_submission_bytes = max_submission_bytes
        self.max_submissions_per_window = max_submissions_per_window
        self.window_seconds = window_seconds
        # {'field': 'str|int|float|bool|dict|list', ...} — STRICT:
        # unmatched fields refuse unless allow_extra_fields.
        self.schema_json = schema_json
        self.allow_extra_fields = allow_extra_fields
        # ballot-box semantics: one submission per identity per value
        # of this payload field ('' = no dedupe).
        self.dedupe_field = dedupe_field
        self.enabled = enabled
        self.notes = notes


class QuarantinedSubmission(treeObject):
    """A caught submission — evidence, not garbage. payload_sample is
    BOUNDED (attackers don't get to fill our disk with their own
    ammunition); the hash identifies the full original."""

    @treeObjectInit
    def __init__(self, name='', rule_name='', app_name='',
                 consumer_identity='', reason='', evidence='',
                 payload_sha256='', payload_sample='',
                 payload_bytes=0, received_at_ms=0, notes='',
                 manager=None):
        self.name = name
        self.rule_name = rule_name
        self.app_name = app_name
        # the RNS identity hash — the census and the cadence both
        # read quarantine counts per identity.
        self.consumer_identity = consumer_identity
        self.reason = reason
        self.evidence = evidence
        self.payload_sha256 = payload_sha256
        self.payload_sample = payload_sample
        self.payload_bytes = payload_bytes
        self.received_at_ms = received_at_ms
        self.notes = notes
