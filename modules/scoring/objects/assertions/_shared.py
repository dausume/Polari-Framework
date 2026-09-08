"""@module scoring.objects.assertions._shared — what the assertions row classes share (constants, seeds, helpers); split from assertions_basis.py (sap-2c)."""
from scoring.agreement_policy_basis import classify_max, policy_bands
from datetime import datetime, timezone
import json

ASSERTION_TYPES = ('score-impact', 'dependency', 'decorative')
DIRECTIONS = ('supports', 'harms')
STATUSES = ('asserted', 'under-review', 'confirmed', 'rejected')
ALLOWED_TRANSITIONS = {
    'asserted': ('under-review', 'confirmed', 'rejected'),
    'under-review': ('confirmed', 'rejected'),
    'confirmed': ('under-review',),
    'rejected': ('under-review',),
}
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def _assertion(manager, name):
    return next((a for a in _rows(manager, 'ScoreAssertion')
                 if getattr(a, 'name', '') == name), None)
def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory managers (selftests) have no db
def transition_assertion(manager, assertion_name, to_status, by='',
                         note=''):
    """Move an assertion through its lifecycle — validated against
    ALLOWED_TRANSITIONS, every move appended to status_history_json
    (history is the tamper-evidence: a flip leaves a visible trail)."""
    row = _assertion(manager, assertion_name)
    if row is None:
        return {'ok': False,
                'error': f"no ScoreAssertion named '{assertion_name}'"}
    if to_status not in STATUSES:
        return {'ok': False,
                'error': f"unknown status '{to_status}'",
                'statuses': list(STATUSES)}
    current = getattr(row, 'status', 'asserted')
    if to_status not in ALLOWED_TRANSITIONS.get(current, ()):
        return {'ok': False,
                'error': f"transition '{current}' → '{to_status}' not "
                         'allowed',
                'allowedFrom': list(
                    ALLOWED_TRANSITIONS.get(current, ())),
                'suggestion': {
                    'knob': 'ScoreAssertion.status',
                    'action': "re-open via 'under-review' first"
                    if current in ('confirmed', 'rejected')
                    else f'move to one of '
                         f'{list(ALLOWED_TRANSITIONS.get(current, ()))}'}}
    try:
        history = json.loads(
            getattr(row, 'status_history_json', '') or '[]')
    except Exception:
        history = []
    entry = {'from': current, 'to': to_status, 'by': by,
             'note': note,
             'at': datetime.now(timezone.utc).isoformat(
                 timespec='seconds')}
    history.append(entry)
    row.status = to_status
    row.status_history_json = json.dumps(history)
    _persist(manager, row)
    return {'ok': True, 'assertion': assertion_name,
            'status': to_status, 'transition': entry,
            'historyLength': len(history)}
def tally_validity(manager, assertion_name, policy_name=''):
    """Per-round validity tallies for one assertion, classified
    through the SAME editable AgreementPolicy direction bands as
    group agreement, ending in a SUGGESTED transition (the status
    knob stays human-held)."""
    row = _assertion(manager, assertion_name)
    if row is None:
        return {'ok': False,
                'error': f"no ScoreAssertion named '{assertion_name}'"}
    policies = _rows(manager, 'AgreementPolicy')
    wanted = policy_name or 'default-agreement'
    policy = next((p for p in policies
                   if getattr(p, 'name', '') == wanted),
                  policies[0] if policies else None)
    bands = policy_bands(policy)['direction'] if policy is not None \
        else []

    votes = [v for v in _rows(manager, 'AssertionValidityVote')
             if getattr(v, 'assertion_name', '') == assertion_name]
    rounds = {}
    for v in votes:
        rounds.setdefault(
            int(getattr(v, 'round_number', 1) or 1), []).append(v)
    round_reports = []
    for number in sorted(rounds):
        tally = {'valid': 0, 'invalid': 0, 'abstain': 0}
        for v in rounds[number]:
            kind = getattr(v, 'vote', 'abstain')
            tally[kind if kind in tally else 'abstain'] += 1
        decisive = tally['valid'] + tally['invalid']
        dominant = (max(tally['valid'], tally['invalid']) / decisive
                    if decisive else 0.5)
        leaning = ('valid' if tally['valid'] > tally['invalid']
                   else 'invalid' if tally['invalid'] > tally['valid']
                   else 'tied')
        round_reports.append({
            'round': number, **tally,
            'dominantFraction': round(dominant, 4),
            'leaning': leaning,
            'band': classify_max(dominant, bands) if bands
            else 'unclassified',
            'voters': sorted(getattr(v, 'voter', '')
                             for v in rounds[number]),
        })

    latest = round_reports[-1] if round_reports else None
    suggestion = None
    if latest is not None:
        strong = latest['band'] in ('large-majority', 'near-consensus',
                                    'consensus')
        if latest['leaning'] == 'valid' and strong:
            suggestion = {
                'knob': 'ScoreAssertion.status',
                'action': "transition to 'confirmed'",
                'evidence': f"round {latest['round']}: "
                            f"{latest['valid']} valid vs "
                            f"{latest['invalid']} invalid "
                            f"({latest['band']})"}
        elif latest['leaning'] == 'invalid' and strong:
            suggestion = {
                'knob': 'ScoreAssertion.status',
                'action': "transition to 'rejected'",
                'evidence': f"round {latest['round']}: "
                            f"{latest['invalid']} invalid vs "
                            f"{latest['valid']} valid "
                            f"({latest['band']})"}
        else:
            suggestion = {
                'knob': 'AssertionValidityVote',
                'action': 'open another round — the latest round is '
                          f"{latest['band']}",
                'evidence': f"round {latest['round']} leaning "
                            f"'{latest['leaning']}' at "
                            f"{latest['dominantFraction']}"}
    return {'ok': True, 'assertion': assertion_name,
            'status': getattr(row, 'status', 'asserted'),
            'agreementPolicy': getattr(policy, 'name', None)
            if policy is not None else None,
            'rounds': round_reports,
            'suggestion': suggestion,
            'note': 'tallies SUGGEST transitions; the status knob is '
                    'moved explicitly via the transition endpoint, '
                    'and every move is history'}
