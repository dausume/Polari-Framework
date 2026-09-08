"""@module scoring.objects.venue_patterns._shared — what the venue_patterns row classes share (constants, seeds, helpers); split from venue_patterns_basis.py (sap-2c)."""
from scoring.assertions_basis import ScoreAssertion
from scoring.worldview_elections_basis import _by_name, _rows
import json

VENUES = ('statute', 'budget-appropriation', 'ballot-initiative',
          'regulation', 'executive-order', 'court-ruling')
ACTIONS = ('introduced', 'enacted', 'funded', 'defunded',
           'omitted-from-budget', 'rider-attached', 'repealed')
SEED_VENUE_PATTERNS = [
    {
        'name': 'policy-via-budget-rider',
        'display_name': 'Policy via budget rider',
        'description': 'An issue is addressed through a budget '
                       'rider with NO enacted statute for the same '
                       'issue beforehand — substantive policy made '
                       'through appropriations rather than '
                       'legislated first and budgeted after.',
        'sequence_rule_json': json.dumps({
            'requires': [{'venue': 'budget-appropriation',
                          'action': 'rider-attached'}],
            'absentBefore': [{'venue': 'statute',
                              'action': 'enacted'}],
        }),
        'severity_note': 'bypasses the deliberative venue where the '
                         'issue would ordinarily be examined',
        'proposed_by': 'seed (Dustin 2026-07-16)',
        'enabled': True,
        'notes': 'the framing is votable content, not baked-in '
                 'judgment',
    },
    {
        'name': 'suppression-by-defunding',
        'display_name': 'Suppression by defunding',
        'description': 'A ballot initiative is enacted by the '
                       'voters, then consecutive budget cycles '
                       'omit or defund it and never fund it — the '
                       'passed measure starved instead of '
                       'implemented.',
        'sequence_rule_json': json.dumps({
            'requires': [{'venue': 'ballot-initiative',
                          'action': 'enacted'}],
            'starvation': {
                'after': {'venue': 'ballot-initiative',
                          'action': 'enacted'},
                'venue': 'budget-appropriation',
                'starvingActions': ['omitted-from-budget',
                                    'defunded'],
                'reliefAction': 'funded',
                'minPeriods': 2,
            },
        }),
        'severity_note': 'inverts the voters\' enacted choice '
                         'through the appropriations venue',
        'proposed_by': 'seed (Dustin 2026-07-16)',
        'enabled': True,
        'notes': 'minPeriods is a knob on the rule — edit the row',
    },
]
def _record_matches(record, matcher):
    if matcher.get('venue') and record.venue != matcher['venue']:
        return False
    if 'action' in matcher and record.action != matcher['action']:
        return False
    if 'action_in' in matcher \
            and record.action not in matcher['action_in']:
        return False
    return True
def _validate_rule(rule):
    """Plain errors naming the constants for unknown venues/actions."""
    matchers = list(rule.get('requires') or []) \
        + list(rule.get('absentBefore') or [])
    starvation = rule.get('starvation')
    if starvation:
        matchers.append(starvation.get('after', {}))
        matchers.append({'venue': starvation.get('venue'),
                         'action_in':
                             starvation.get('starvingActions', [])})
        matchers.append({'action': starvation.get('reliefAction')})
    for matcher in matchers:
        venue = matcher.get('venue')
        if venue and venue not in VENUES:
            raise ValueError(
                f'rule references unknown venue {venue!r} — venues: '
                f'{", ".join(VENUES)}')
        actions = ([matcher['action']] if 'action' in matcher
                   and matcher['action'] else []) \
            + list(matcher.get('action_in') or [])
        for action in actions:
            if action not in ACTIONS:
                raise ValueError(
                    f'rule references unknown action {action!r} — '
                    f'actions: {", ".join(ACTIONS)}')
def _apply_rule(rule, records):
    """records chronological (occurred_at). -> None or
    {'matched': [records], 'anchorAt': iso}."""
    _validate_rule(rule)
    matched = []
    last_required_at = ''
    for matcher in rule.get('requires') or []:
        hit = next((r for r in records
                    if _record_matches(r, matcher)), None)
        if hit is None:
            return None
        matched.append(hit)
        last_required_at = max(last_required_at, hit.occurred_at)
    for matcher in rule.get('absentBefore') or []:
        blocker = next(
            (r for r in records
             if _record_matches(r, matcher)
             and r.occurred_at <= last_required_at), None)
        if blocker is not None:
            return None  # the legitimate sequence — no finding
    starvation = rule.get('starvation')
    if starvation:
        anchor = next((r for r in records
                       if _record_matches(r, starvation['after'])),
                      None)
        if anchor is None:
            return None
        window = [r for r in records
                  if r.venue == starvation['venue']
                  and r.occurred_at > anchor.occurred_at]
        periods = []
        for record in window:  # chronological already
            if not periods or periods[-1][0] != record.fiscal_period:
                periods.append((record.fiscal_period, []))
            periods[-1][1].append(record)
        streak, streak_records = 0, []
        for _, period_records in periods:
            actions = {r.action for r in period_records}
            if starvation['reliefAction'] in actions:
                return None  # funded before the streak completed
            if actions & set(starvation['starvingActions']):
                streak += 1
                streak_records.extend(period_records)
                if streak >= int(starvation.get('minPeriods', 2)):
                    return {'matched': matched + streak_records,
                            'anchorAt': anchor.occurred_at}
            else:
                streak, streak_records = 0, []
        return None
    return {'matched': matched, 'anchorAt': last_required_at}
def _record_summary(record):
    return {'name': record.name, 'occurredAt': record.occurred_at,
            'venue': record.venue, 'action': record.action,
            'fiscalPeriod': record.fiscal_period,
            'actor': record.actor_subject_name}
def detect_patterns(manager, issue_name):
    """Interpret every enabled pattern over one issue's records.
    Findings state that a sequence MATCHES a pattern — with the
    records and actors as evidence — and never declare wrongdoing."""
    records = sorted(
        (r for r in _rows(manager, 'VenueActionRecord')
         if getattr(r, 'issue_name', '') == issue_name),
        key=lambda r: getattr(r, 'occurred_at', ''))
    if not records:
        known = sorted({getattr(r, 'issue_name', '')
                        for r in _rows(manager, 'VenueActionRecord')
                        if getattr(r, 'issue_name', '')})
        if known:
            return {'ok': False,
                    'error': f"no VenueActionRecord rows for issue "
                             f"'{issue_name}'",
                    'knownIssues': known}
        return {'ok': False,
                'error': 'no VenueActionRecord rows exist yet',
                'suggestion': {
                    'knob': 'VenueActionRecord',
                    'action': 'record the issue\'s actions per '
                              'venue (statute, budget, initiative…) '
                              'so sequences become analyzable'}}
    patterns = [p for p in _rows(manager, 'VenueMismatchPattern')
                if getattr(p, 'enabled', True)]
    if not patterns:
        return {'ok': False,
                'error': 'no enabled VenueMismatchPattern rows',
                'suggestion': {
                    'knob': 'VenueMismatchPattern',
                    'action': 'seed or enable pattern rows — the '
                              'catalog is editable content'}}
    findings, rule_errors = [], []
    for pattern in patterns:
        try:
            rule = json.loads(pattern.sequence_rule_json or '{}')
            match = _apply_rule(rule, records)
        except (ValueError, json.JSONDecodeError) as exc:
            rule_errors.append({'pattern': pattern.name,
                                'error': str(exc)})
            continue
        if match is None:
            continue
        summaries = [_record_summary(r) for r in match['matched']]
        actors = sorted({s['actor'] for s in summaries
                         if s['actor']})
        narrative = (
            f"issue '{issue_name}' matches the "
            f"'{pattern.display_name}' sequence: "
            + '; '.join(f"{s['action']} in {s['venue']}"
                        + (f" ({s['fiscalPeriod']})"
                           if s['fiscalPeriod'] else '')
                        + f" on {s['occurredAt'][:10]}"
                        for s in summaries))
        findings.append({'pattern': pattern.name,
                         'patternDisplay': pattern.display_name,
                         'issue': issue_name,
                         'matchedRecords': summaries,
                         'actors': actors,
                         'narrative': narrative})
    result = {'ok': True, 'issue': issue_name,
              'recordCount': len(records), 'findings': findings}
    if rule_errors:
        result['ruleErrors'] = rule_errors
    return result
def file_pattern_assertion(manager, finding, asserted_by):
    """Materialize one finding as REAL ScoreAssertions (one per
    implicated actor), status 'asserted' — the scr-6 validity-vote
    machinery adjudicates; nothing is auto-confirmed."""
    if not finding.get('actors'):
        return {'ok': False,
                'error': 'the finding implicates no actor subjects '
                         '— record actor_subject_name on the '
                         'VenueActionRecord rows'}
    if not asserted_by:
        return {'ok': False,
                'error': 'asserted_by is required — assertions '
                         'carry accountability'}
    created = []
    table = manager.objectTables.setdefault('ScoreAssertion', {})
    for actor in finding['actors']:
        name = (f"assert-venue-{finding['pattern']}-"
                f"{finding['issue']}-{actor}")
        if any(getattr(r, 'name', '') == name
               for r in table.values()):
            created.append({'name': name, 'created': False})
            continue
        assertion = ScoreAssertion(
            name=name,
            display_name=f"{finding['patternDisplay']} — "
                         f"{finding['issue']} ({actor})",
            subject_name=actor,
            intent=finding['narrative'],
            assertion_type='score-impact',
            direction='harms',
            strength=0.5,
            asserted_by=asserted_by,
            status='asserted',
            status_history_json='[]',
            provenance_id='scoring.venue_patterns_basis.detect_patterns',
            notes='matched records: '
                  + ', '.join(s['name']
                              for s in finding['matchedRecords'])
                  + ' — a sequence match filed for validity '
                    'review, not a confirmed judgment',
            manager=manager)
        if not any(existing is assertion
                   for existing in table.values()):
            table[name] = assertion
        try:
            db = getattr(manager, 'db', None)
            if db is not None:
                db.saveInstanceInDB(assertion)
        except Exception:
            pass
        created.append({'name': name, 'created': True})
    return {'ok': True, 'assertions': created,
            'status': 'asserted',
            'note': 'validity votes (scr-6) adjudicate — never '
                    'auto-confirmed'}
