"""@module scoring.objects.contributors._shared — what the contributors row classes share (constants, seeds, helpers); split from contributors_basis.py (sap-2c)."""
import json

CONTRIBUTOR_KINDS = ('individual', 'organization', 'lobby',
                     'institution', 'coalition')
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def contributor_record(manager, name):
    """One contributor's accountable track record: their assertions by
    status (confirmation rate = how their claims survived validity
    review), validity votes cast, evidence submitted, values ingested.
    Honest 404 for unknown names."""
    row = next((r for r in _rows(manager, 'Contributor')
                if getattr(r, 'name', '') == name), None)
    if row is None:
        return {'ok': False,
                'error': f"no Contributor named '{name}'",
                'knownContributors': sorted(
                    getattr(r, 'name', '')
                    for r in _rows(manager, 'Contributor'))}

    assertions = [a for a in _rows(manager, 'ScoreAssertion')
                  if getattr(a, 'asserted_by', '') == name]
    by_status = {}
    for a in assertions:
        status = getattr(a, 'status', 'asserted')
        by_status[status] = by_status.get(status, 0) + 1
    reviewed = by_status.get('confirmed', 0) + by_status.get(
        'rejected', 0)
    votes = [v for v in _rows(manager, 'AssertionValidityVote')
             if getattr(v, 'voter', '') == name]
    evidence = [e for e in _rows(manager, 'MediaEvidence')
                if getattr(e, 'submitted_by', '') == name]
    values = [v for v in _rows(manager, 'ContextualizedValue')
              if getattr(v, 'contributed_by', '') == name]

    try:
        affiliations = json.loads(
            getattr(row, 'affiliations_json', '') or '[]')
    except Exception:
        affiliations = []
    return {
        'ok': True,
        'contributor': name,
        'displayName': getattr(row, 'display_name', '') or name,
        'kind': getattr(row, 'kind', ''),
        'pseudonymous': bool(getattr(row, 'pseudonymous', True)),
        'affiliations': affiliations,
        'assertions': {
            'total': len(assertions),
            'byStatus': by_status,
            # Of the assertions that finished review, how many held
            # up — the lobby-accountability number.
            'confirmationRate': (
                round(by_status.get('confirmed', 0) / reviewed, 4)
                if reviewed else None),
            'reviewed': reviewed,
            'names': sorted(getattr(a, 'name', '')
                            for a in assertions),
        },
        'validityVotesCast': len(votes),
        'evidenceSubmitted': sorted(getattr(e, 'name', '')
                                    for e in evidence),
        'valuesContributed': len(values),
        'note': ('confirmationRate is None until at least one of this '
                 "contributor's assertions finishes validity review"
                 if not reviewed else ''),
    }
SEED_CONTRIBUTORS = [
    {
        'name': 'demo-citizen-jane',
        'display_name': 'citizen-jane (pseudonym)',
        'kind': 'individual',
        'pseudonymous': True,
        'description': 'Demo pseudonymous individual contributor — a '
                       'track record without a legal identity.',
    },
    {
        'name': 'demo-labor-lobby',
        'display_name': 'Demo Labor Lobby',
        'kind': 'lobby',
        'pseudonymous': False,
        'identity_ref_json': json.dumps(
            {'kind': 'external', 'url': 'https://example.org/lobby'}),
        'description': 'Demo disclosed lobby — its scorecard '
                       'assertions accrue to an accountable record.',
    },
    {
        'name': 'demo-research-group',
        'display_name': 'Demo Research Group',
        'kind': 'organization',
        'pseudonymous': False,
        'description': 'Demo research org contributing data series — '
                       'accountable for research statements.',
    },
]
