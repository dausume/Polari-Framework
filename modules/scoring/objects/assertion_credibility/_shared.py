"""@module scoring.objects.assertion_credibility._shared — what the assertion_credibility row classes share (constants, seeds, helpers); split from assertion_credibility_basis.py (sap-2c)."""
from scoring.survival_costs_basis import SMALL_SAMPLE

CREDIBILITY_LEVELS = ('credible', 'questionable', 'not-credible')
CREDIBILITY_WEIGHTS = {'credible': 1.0, 'questionable': 0.5,
                       'not-credible': 0.0}
CREDIBILITY_PRIOR = 1.0
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def _by_name(manager, class_name, name):
    return next((r for r in _rows(manager, class_name)
                 if getattr(r, 'name', '') == name), None)
def _persist(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
def _unit_key(vote):
    """The counted unit: the group when the vote is a stance, else
    the individual (mirrors cross_validation's confirmer keying)."""
    group = getattr(vote, 'on_behalf_of_group', '')
    return group or f'individual:{getattr(vote, "voter", "")}'
def assertion_credibility_reading(manager, assertion_name):
    """The weighted community reading: each DISTINCT unit's LATEST
    vote, scored credible=1 / questionable=0.5 / not-credible=0 over
    (units + prior) — bounded below 1 by construction, exactly the
    sourcing_credibility formula. Parallel to (never a substitute
    for) the scr-6 validity lifecycle."""
    assertion = _by_name(manager, 'ScoreAssertion', assertion_name)
    if assertion is None:
        known = sorted(getattr(a, 'name', '')
                       for a in _rows(manager, 'ScoreAssertion'))
        return {'ok': False,
                'error': f"no ScoreAssertion named "
                         f"'{assertion_name}'",
                'knownAssertions': known}
    votes = [v for v in _rows(manager, 'AssertionCredibilityVote')
             if getattr(v, 'assertion_name', '') == assertion_name]
    if not votes:
        return {'ok': True, 'score': None, 'voteCount': 0,
                'validityStatus': getattr(assertion, 'status', ''),
                'reading': 'no credibility votes yet — credibility '
                           'unrated, not zero',
                'suggestion': {
                    'knob': 'cast_credibility_vote',
                    'action': 'groups and individuals vote on the '
                              "assertion's credibility with "
                              'rationale + evidence'}}
    latest_by_unit = {}
    for vote in sorted(votes,
                       key=lambda v: getattr(v, 'cast_at', '')):
        latest_by_unit[_unit_key(vote)] = vote
    weights = {unit: CREDIBILITY_WEIGHTS.get(
                   getattr(v, 'credibility', ''), 0.0)
               for unit, v in latest_by_unit.items()}
    score = sum(weights.values()) / (len(weights)
                                     + CREDIBILITY_PRIOR)
    current = [getattr(v, 'credibility', '')
               for v in latest_by_unit.values()]
    groups = sorted(u for u in latest_by_unit
                    if not u.startswith('individual:'))
    individuals = sorted(u.split(':', 1)[1] for u in latest_by_unit
                         if u.startswith('individual:'))
    evidence = []
    for unit, vote in sorted(latest_by_unit.items()):
        kind = ('group stance' if not unit.startswith('individual:')
                else 'individual')
        entry = (f'{unit} ({kind}): '
                 f'{getattr(vote, "credibility", "")} — '
                 f'{getattr(vote, "rationale", "") or "no rationale"}')
        url = getattr(vote, 'cited_evidence_url', '')
        if url:
            entry += f' [{url}]'
        evidence.append(entry)
    return {'ok': True, 'score': round(score, 4),
            'voteCount': len(votes),
            'distinctUnits': len(latest_by_unit),
            'groupStances': groups,
            'individualVoters': individuals,
            'credibleCount': current.count('credible'),
            'questionableCount': current.count('questionable'),
            'notCredibleCount': current.count('not-credible'),
            'supersededVotes': len(votes) - len(latest_by_unit),
            'smallSample': len(latest_by_unit) < SMALL_SAMPLE,
            'validityStatus': getattr(assertion, 'status', ''),
            'reading': 'a credibility READING with evidence, not a '
                       'truth declaration — the scr-6 validity '
                       'lifecycle remains the status adjudicator',
            'evidence': evidence}
