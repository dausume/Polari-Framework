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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/policy_votes/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_basis import ScoreSubject

from scoring.objects.policy_votes._shared import SEED_COHORT_GROUPS, SEED_POLICY_VOTES, SEED_POLITICIAN_SUBJECTS, VOTE_KINDS, _names, _rows, _slug  # noqa: F401
from scoring.objects.policy_votes.PolicyVote import PolicyVote  # noqa: F401

from scoring.scoring_basis import ScoreSubject

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
