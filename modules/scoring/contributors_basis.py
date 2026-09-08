"""
@cross-cutting
@module scoring.contributors_basis
@tags @xc:bindings

Contributor — WHO contributes (scr-5). Dustin 2026-07-08: "individuals
contributing data and we should be able to track individuals and orgs
(or allow them to stay anonymous under pseudonames) for research
contributions … hold groups accountable for research statements,
lobbies for their own scorecard assertions".

A Contributor row is an identity handle: an individual, organization,
lobby, or institution. Pseudonymity is a KNOB on the row — a
pseudonymous contributor is still one accountable track record, just
not a legal identity. Assertions (asserted_by), validity votes
(voter), evidence (submitted_by) and ingested values (contributed_by)
all key to contributor names, so a contributor's record — how many of
their assertions survived validity review, what they ingested — is
computable, which is exactly what holds lobbies accountable for their
own scorecard assertions.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (GET /api/scoring/contributors/{name}/record)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: Contributor kinds — who can be held accountable for contributions.
CONTRIBUTOR_KINDS = ('individual', 'organization', 'lobby',
                     'institution', 'coalition')


class Contributor(treeObject):
    """One accountable contribution identity (real or pseudonymous)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key — for pseudonymous contributors this
        # IS the pseudonym ('watchdog-42').
        name: str = '',
        display_name: str = '',
        # CONTRIBUTOR_KINDS entry.
        kind: str = 'individual',
        # Pseudonymous = no real-world identity attached; the track
        # record still accrues to this row. Default True — identity
        # disclosure is opt-in, never assumed.
        pseudonymous: bool = True,
        # Optional identity anchor when disclosed (JSON objectRef or
        # {'kind': 'external', 'url'/'orcid'/'ein': ...}). Empty for
        # pseudonymous rows.
        identity_ref_json: str = '',
        # Other contributor names this one is affiliated with (JSON
        # list) — an individual funded by / working for a lobby is a
        # visible edge, not hidden.
        affiliations_json: str = '[]',
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.pseudonymous = pseudonymous
        self.identity_ref_json = identity_ref_json
        self.affiliations_json = affiliations_json
        self.description = description
        self.notes = notes


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
