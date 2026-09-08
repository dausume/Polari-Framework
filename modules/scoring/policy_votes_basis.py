"""
@cross-cutting
@module scoring.policy_votes_basis
@tags @xc:bindings

PolicyVote (scr-6) — one politician's recorded vote on one policy
subject. Dustin 2026-07-08: "We should track politician voting on
policies, which should in theory be available via an API somewhere
publically."

The public-API path is the EXISTING pipeline: api-profiler turns an
external API (Congress.gov v3, GovTrack, OpenStates) into a local
class; ingest_votes_from_class maps that class's rows into PolicyVote
rows — no bespoke ETL. Honesty knobs mirror data_ingestion: unknown
politicians/policies REFUSE unless the create knobs are explicitly
set; existing votes are skipped, never clobbered, unless overwrite.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.politician_scoring / scoring.scoring_api
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_basis import ScoreSubject

VOTE_KINDS = ('yea', 'nay', 'abstain')


class PolicyVote(treeObject):
    """One recorded vote: politician × policy."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('vote-rivera-fair-wage-act').
        name: str = '',
        # ScoreSubject names (kind 'politician' / kind 'policy').
        politician_name: str = '',
        policy_name: str = '',
        # VOTE_KINDS entry.
        vote: str = 'abstain',
        # ISO date — politician scores are time-scoped through this
        # (scr-4 frames).
        vote_date: str = '',
        chamber: str = '',
        session: str = '',
        source: str = '',
        provenance_id: str = '',
        # Contributor who ingested/recorded this vote.
        contributed_by: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.politician_name = politician_name
        self.policy_name = policy_name
        self.vote = vote
        self.vote_date = vote_date
        self.chamber = chamber
        self.session = session
        self.source = source
        self.provenance_id = provenance_id
        self.contributed_by = contributed_by
        self.notes = notes


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _names(manager, class_name):
    return {getattr(r, 'name', '') for r in _rows(manager, class_name)}


def _slug(text):
    return str(text).strip().lower().replace(' ', '-')


def ingest_votes_from_class(manager, payload):
    """ANY object class (usually one the api-profiler created from a
    public vote API) → PolicyVote rows.

    payload: {'source_class': <objectTables class name>,
              'mapping': {'politicianField', 'policyField',
                          'voteField', 'dateField'?, 'chamberField'?},
              'vote_values': {<raw>: 'yea'|'nay'|'abstain'}  optional
                             raw-value translation ('Yea', 'Aye'…),
              'create_missing_politicians': bool (default False),
              'create_missing_policies': bool  (default False),
              'overwrite': bool                (default False),
              'source': str, 'provenance': str,
              'contributed_by': str}
    """
    source_class = payload.get('source_class', '')
    mapping = payload.get('mapping', {}) or {}
    pol_field = mapping.get('politicianField', '')
    policy_field = mapping.get('policyField', '')
    vote_field = mapping.get('voteField', '')
    if not source_class or not pol_field or not policy_field \
            or not vote_field:
        return {'ok': False,
                'error': "payload needs 'source_class' and a "
                         "'mapping' with politicianField + "
                         'policyField + voteField'}
    rows = _rows(manager, source_class)
    if not rows:
        return {'ok': False,
                'error': f"class '{source_class}' has no rows",
                'classesWithRows': sorted(
                    k for k, v in (manager.objectTables or {}).items()
                    if v)[:40]}

    vote_values = payload.get('vote_values', {}) or {}
    known_subjects = _names(manager, 'ScoreSubject')
    create_pols = bool(payload.get('create_missing_politicians'))
    create_policies = bool(payload.get('create_missing_policies'))
    overwrite = bool(payload.get('overwrite'))

    # Pre-flight: every refusal in one answer (data_ingestion idiom).
    missing_pols, missing_policies, bad_votes = set(), set(), []
    parsed = []
    for row in rows:
        politician = _slug(getattr(row, pol_field, '') or '')
        policy = _slug(getattr(row, policy_field, '') or '')
        raw_vote = getattr(row, vote_field, '')
        vote = vote_values.get(raw_vote, str(raw_vote).lower())
        if not politician or not policy:
            bad_votes.append({'row': getattr(row, 'name', '?'),
                              'error': 'missing politician/policy '
                                       'field'})
            continue
        if vote not in VOTE_KINDS:
            bad_votes.append({'row': getattr(row, 'name', '?'),
                              'error': f"vote '{raw_vote}' not in "
                                       f'{list(VOTE_KINDS)} — map it '
                                       "via 'vote_values'"})
            continue
        if politician not in known_subjects:
            missing_pols.add(politician)
        if policy not in known_subjects:
            missing_policies.add(policy)
        parsed.append((row, politician, policy, vote))
    if missing_pols and not create_pols:
        return {'ok': False,
                'error': f'unknown politicians: {sorted(missing_pols)}',
                'suggestion': {'knob': 'create_missing_politicians',
                               'action': 'set true to create these '
                                         "ScoreSubject rows (kind "
                                         "'politician')"}}
    if missing_policies and not create_policies:
        return {'ok': False,
                'error': f'unknown policies: '
                         f'{sorted(missing_policies)}',
                'suggestion': {'knob': 'create_missing_policies',
                               'action': 'set true to create these '
                                         "ScoreSubject rows (kind "
                                         "'policy') — scores still "
                                         'need assertions'}}
    for name in sorted(missing_pols):
        ScoreSubject(name=name,
                     display_name=name.replace('-', ' ').title(),
                     kind='politician',
                     description='created by vote ingestion',
                     manager=manager)
    for name in sorted(missing_policies):
        ScoreSubject(name=name,
                     display_name=name.replace('-', ' ').title(),
                     kind='policy',
                     description='created by vote ingestion',
                     manager=manager)

    existing = {getattr(r, 'name', ''): r
                for r in _rows(manager, 'PolicyVote')}
    created, updated, skipped = [], [], []
    for row, politician, policy, vote in parsed:
        name = f'vote-{politician}@{policy}'
        date = str(getattr(row, mapping.get('dateField', ''), '')
                   or '') if mapping.get('dateField') else ''
        chamber = str(getattr(row, mapping.get('chamberField', ''),
                              '') or '') \
            if mapping.get('chamberField') else ''
        if name in existing:
            if not overwrite:
                skipped.append(name)
                continue
            vote_row = existing[name]
            vote_row.vote = vote
            vote_row.vote_date = date
            vote_row.chamber = chamber
            vote_row.source = payload.get('source', '')
            vote_row.provenance_id = payload.get('provenance', '')
            vote_row.contributed_by = payload.get(
                'contributed_by', '')
            try:
                manager.db.saveInstanceInDB(vote_row)
            except Exception:
                pass
            updated.append(name)
            continue
        PolicyVote(name=name, politician_name=politician,
                   policy_name=policy, vote=vote, vote_date=date,
                   chamber=chamber,
                   source=payload.get(
                       'source', f'class series {source_class}'),
                   provenance_id=payload.get('provenance', ''),
                   contributed_by=payload.get('contributed_by', ''),
                   manager=manager)
        created.append(name)

    return {'ok': True, 'sourceClass': source_class,
            'created': created, 'updated': updated,
            'skipped': skipped, 'refused': bad_votes,
            'createdPoliticians': sorted(missing_pols),
            'createdPolicies': sorted(missing_policies),
            'overwrite': overwrite}


SEED_POLICY_VOTES = [
    {
        'name': 'vote-pol-rivera@policy-fair-wage-act',
        'politician_name': 'pol-rivera',
        'policy_name': 'policy-fair-wage-act',
        'vote': 'yea', 'vote_date': '2024-04-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-rivera@policy-labor-standards-2020',
        'politician_name': 'pol-rivera',
        'policy_name': 'policy-labor-standards-2020',
        'vote': 'yea', 'vote_date': '2020-06-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-stone@policy-fair-wage-act',
        'politician_name': 'pol-stone',
        'policy_name': 'policy-fair-wage-act',
        'vote': 'nay', 'vote_date': '2024-04-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-stone@policy-labor-standards-2020',
        'politician_name': 'pol-stone',
        'policy_name': 'policy-labor-standards-2020',
        'vote': 'abstain', 'vote_date': '2020-06-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call — abstention is a '
                         'participation gap, surfaced not scored',
    },
]

SEED_POLITICIAN_SUBJECTS = [
    {
        'name': 'pol-rivera', 'display_name': 'Rep. Rivera (demo)',
        'kind': 'politician',
        'description': 'Demo politician — voted yea on both labor '
                       'policies.',
    },
    {
        'name': 'pol-stone', 'display_name': 'Rep. Stone (demo)',
        'kind': 'politician',
        'description': 'Demo politician — nay on the Fair Wage Act, '
                       'abstained on Labor Standards.',
    },
]

SEED_COHORT_GROUPS = [
    {
        'name': 'demo-assembly-labor-committee',
        'display_name': 'Assembly Labor Committee (demo)',
        'group_type': 'political',
        'member_subject_names_json': json.dumps(
            ['pol-rivera', 'pol-stone']),
        'description': 'Demo politician cohort — the split votes '
                       'exercise the divisive cohort read.',
    },
]
