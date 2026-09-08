"""@module scoring.objects.credibility_bases._shared — what the credibility_bases row classes share (constants, seeds, helpers); split from credibility_bases_basis.py (sap-2c)."""
from datetime import datetime, timezone
import json

BASIS_KINDS = ('professional', 'impact', 'methodological',
               'institutional', 'independent-review', 'locality')
CLAIM_STATUSES = ('claimed', 'attested', 'disputed')
CLAIM_TRANSITIONS = {
    'claimed': ('attested', 'disputed'),
    'attested': ('disputed', 'claimed'),
    'disputed': ('attested', 'claimed'),
}
STANCE_KINDS = {
    'proof-rebuttal': ('ProofRebuttal', 'raised_by', 'proof_name'),
    'proof-vote': ('ProofVote', 'voter', 'proof_name'),
    'assertion-credibility-vote': ('AssertionCredibilityVote',
                                   'voter', 'assertion_name'),
    'term-relation-assertion': ('TermRelationAssertion',
                                'asserted_by', None),
    'scope-vote': ('TermScopeVote', 'voter', None),
}
SMALL_SAMPLE = 5
_READING_NOTE = ('a credibility-basis reading with evidence, not a '
                 'truth declaration')
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)
def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r
            for r in _rows(manager, class_name)}
def _persist(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
def _stamp(at=''):
    return at or datetime.now(timezone.utc).isoformat()
def _unit_key(vote):
    group = getattr(vote, 'on_behalf_of_group', '')
    return group or f'individual:{getattr(vote, "voter", "")}'
def _attester_unit(row):
    group = getattr(row, 'on_behalf_of_group', '')
    return group or f'individual:{getattr(row, "attester", "")}'
def _latest_by_unit(rows, unit_fn):
    latest = {}
    for row in sorted(rows, key=lambda r: getattr(r, 'cast_at', '')):
        latest[unit_fn(row)] = row
    return latest
def _contributor_exists(manager, name):
    return name in _by_name(manager, 'Contributor')
def _append_history(claim, event, by='', at=''):
    history = json.loads(claim.status_history_json or '[]')
    history.append({'event': event, 'by': by, 'at': _stamp(at)})
    claim.status_history_json = json.dumps(history)
def attestation_tally(manager, claim_name):
    rows = [a for a in _rows(manager, 'ClaimAttestation')
            if getattr(a, 'claim_name', '') == claim_name]
    latest = _latest_by_unit(rows, _attester_unit)
    supporting = sorted(u for u, a in latest.items() if a.supports)
    opposing = sorted(u for u, a in latest.items()
                      if not a.supports)
    return {'claim': claim_name, 'units': len(latest),
            'supportingUnits': supporting,
            'opposingUnits': opposing,
            'smallSample': len(latest) < SMALL_SAMPLE}
def apply_attestation_verdict(manager, claim_name, by=''):
    """The explicit act: majority support -> 'attested'; majority
    opposition -> 'disputed'; ties/empty refuse with the counts.
    Never automatic on a cast."""
    claim = _by_name(manager, 'CredibilityClaim').get(claim_name)
    if claim is None:
        return {'ok': False,
                'error': f"no CredibilityClaim named '{claim_name}'"}
    tally = attestation_tally(manager, claim_name)
    support = len(tally['supportingUnits'])
    oppose = len(tally['opposingUnits'])
    if support == oppose:
        return {'ok': False,
                'error': f'attestation is tied or empty '
                         f'({support} for / {oppose} against) — '
                         'no verdict to apply',
                'tally': tally}
    to_status = 'attested' if support > oppose else 'disputed'
    if to_status not in CLAIM_TRANSITIONS.get(claim.status, ()):
        return {'ok': False,
                'error': f"transition '{claim.status}' → "
                         f"'{to_status}' not allowed",
                'transitions': CLAIM_TRANSITIONS}
    claim.status = to_status
    _append_history(claim, to_status, by=by)
    _persist(manager, claim)
    return {'ok': True, 'claim': claim_name, 'status': to_status,
            'tally': tally}
def _context_chain(manager, context_name):
    """The name + its parent chain (loop-guarded)."""
    contexts = _by_name(manager, 'ScoreContext')
    chain, current, seen = [], context_name, set()
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        row = contexts.get(current)
        current = getattr(row, 'parent_name', '') if row else ''
    return chain
def _scope_covers(manager, claim, subject_contexts):
    """True/False/None: does the claim's domain cover any of the
    stance's subject contexts (exact or ancestor/descendant along
    parent chains)? None = undeterminable (no subject contexts)."""
    domain = json.loads(claim.domain_scope_json or '[]')
    if not domain:
        return None
    if not subject_contexts:
        return None
    for subject in subject_contexts:
        subject_chain = set(_context_chain(manager, subject))
        for dom in domain:
            if dom in subject_chain:
                return True
            if subject in set(_context_chain(manager, dom)):
                return True
    return False
def _stance_subject_contexts(manager, stance_kind, stance):
    """The contexts a stance is ABOUT, where determinable."""
    if stance_kind in ('proof-rebuttal', 'proof-vote'):
        proof = _by_name(manager, 'TermProof').get(
            getattr(stance, 'proof_name', ''))
        if proof is not None:
            return json.loads(proof.context_scope_json or '[]')
    return []
def _basis_descriptor(manager, claim, scope_covered):
    label = claim.basis_kind
    if claim.qualifier:
        label += f':{claim.qualifier}'
    parts = []
    affiliations = json.loads(claim.affiliations_json or '[]')
    for a in affiliations:
        parts.append(f"{a.get('relation', 'affiliated')}: "
                     f"{a.get('org', '?')}")
    conflicts = json.loads(claim.declared_conflicts_json or '[]')
    if conflicts:
        parts.append(f'conflicts declared: {len(conflicts)}')
    if claim.independence_note:
        note = 'independent'
        if claim.status == 'attested':
            note += ' — attested absence of ties'
        else:
            note += f' ({claim.status})'
        parts.append(note)
    elif claim.status == 'attested':
        parts.append('attested')
    elif claim.status == 'disputed':
        parts.append('DISPUTED')
    if scope_covered is False:
        parts.append('basis outside its claimed domain')
    detail = f" ({'; '.join(parts)})" if parts else ''
    return f'{label}{detail}'
def _links_for(manager, stance_kind, names):
    wanted = set(names)
    return [l for l in _rows(manager, 'StanceBasis')
            if getattr(l, 'stance_kind', '') == stance_kind
            and getattr(l, 'stance_name', '') in wanted]
def _stance_entry(manager, stance_kind, stance):
    """One stance's by-basis entry (with or without a link)."""
    table, actor_field, _lf = STANCE_KINDS[stance_kind]
    entry = {'stanceKind': stance_kind,
             'stance': getattr(stance, 'name', ''),
             'actor': getattr(stance, actor_field, '')}
    if stance_kind == 'proof-rebuttal':
        entry['challenge'] = getattr(stance, 'challenge_kind', '')
        entry['rationale'] = getattr(stance, 'rationale', '')
        entry['status'] = getattr(stance, 'status', '')
    elif stance_kind == 'proof-vote':
        entry['voteKind'] = getattr(stance, 'vote_kind', '')
        entry['choice'] = getattr(stance, 'choice', '')
    elif stance_kind == 'assertion-credibility-vote':
        entry['credibility'] = getattr(stance, 'credibility', '')
    elif stance_kind == 'term-relation-assertion':
        entry['relation'] = getattr(stance, 'relation', '')
        entry['relatedTerm'] = getattr(stance, 'related_term', '')
    return entry
def _group_by_basis(manager, stances_by_kind):
    """{basisLabel: [entries]}, plus the unattributed bucket. Kinds
    are NEVER collapsed — there is deliberately no cross-basis
    score."""
    claims = _by_name(manager, 'CredibilityClaim')
    by_basis, unattributed = {}, []
    for stance_kind, stances in stances_by_kind.items():
        links = {l.stance_name: l for l in _links_for(
            manager, stance_kind,
            [getattr(s, 'name', '') for s in stances])}
        for stance in stances:
            entry = _stance_entry(manager, stance_kind, stance)
            link = links.get(getattr(stance, 'name', ''))
            claim = claims.get(link.claim_name) if link else None
            if claim is None:
                entry['basis'] = 'unattributed'
                unattributed.append(entry)
                continue
            covered = _scope_covers(
                manager, claim,
                _stance_subject_contexts(manager, stance_kind,
                                         stance))
            entry['basis'] = _basis_descriptor(manager, claim,
                                               covered)
            entry['claim'] = claim.name
            if covered is False:
                entry['scopeNote'] = ('basis outside its claimed '
                                      'domain')
            key = claim.basis_kind + (f':{claim.qualifier}'
                                      if claim.qualifier else '')
            by_basis.setdefault(key, []).append(entry)
    return by_basis, unattributed
def proof_reading_by_basis(manager, proof_name):
    """The real proof_reading, then the by-basis breakdown joined
    from StanceBasis links. Base fields are IDENTICAL to
    proof_reading — consumers not asking for bases see no change."""
    from scoring.term_proofs_basis import proof_reading
    base = proof_reading(manager, proof_name)
    if not base.get('ok'):
        return base
    rebuttals = [r for r in _rows(manager, 'ProofRebuttal')
                 if getattr(r, 'proof_name', '') == proof_name]
    votes = [v for v in _rows(manager, 'ProofVote')
             if getattr(v, 'proof_name', '') == proof_name]
    by_basis, unattributed = _group_by_basis(
        manager, {'proof-rebuttal': rebuttals, 'proof-vote': votes})
    return dict(base, byBasis=by_basis, unattributed=unattributed,
                basisNote=_READING_NOTE)
def assertion_reading_by_basis(manager, assertion_name):
    from scoring.assertion_credibility_basis import (
        assertion_credibility_reading)
    base = assertion_credibility_reading(manager, assertion_name)
    if not base.get('ok'):
        return base
    stances = [v for v in _rows(manager, 'AssertionCredibilityVote')
               if getattr(v, 'assertion_name', '')
               == assertion_name]
    by_basis, unattributed = _group_by_basis(
        manager, {'assertion-credibility-vote': stances})
    return dict(base, byBasis=by_basis, unattributed=unattributed,
                basisNote=_READING_NOTE)
def qualification_relevance(manager, context_name):
    """Which basis kinds/qualifiers the community deems relevant for
    THIS context — ranked by distinct-unit support. A ranking
    reading; it orders attention, it excludes nobody."""
    votes = [v for v in _rows(manager, 'QualificationRelevanceVote')
             if getattr(v, 'context_name', '') == context_name]
    if not votes:
        return {'ok': True, 'context': context_name, 'ranking': [],
                'reading': _READING_NOTE,
                'suggestion': {
                    'knob': 'cast_relevance_vote',
                    'action': 'no relevance votes for this context '
                              'yet — vote on which qualification '
                              'kinds matter here'}}
    grouped = {}
    for vote in votes:
        key = (vote.basis_kind, getattr(vote, 'qualifier', ''))
        grouped.setdefault(key, []).append(vote)
    ranking = []
    for (kind, qualifier), rows in grouped.items():
        latest = _latest_by_unit(rows, _unit_key)
        support = sum(1 for v in latest.values() if v.relevant)
        oppose = len(latest) - support
        ranking.append({
            'basisKind': kind, 'qualifier': qualifier,
            'label': kind + (f':{qualifier}' if qualifier else ''),
            'supportUnits': support, 'opposeUnits': oppose,
            'units': len(latest),
            'smallSample': len(latest) < SMALL_SAMPLE})
    ranking.sort(key=lambda e: (-e['supportUnits'],
                                e['opposeUnits'], e['label']))
    return {'ok': True, 'context': context_name,
            'ranking': ranking, 'reading': _READING_NOTE}
def _rank_positions(ranking):
    positions = {}
    for index, entry in enumerate(ranking):
        positions[entry['label']] = index
        # A qualified label also anchors its bare kind (weaker).
        positions.setdefault(entry['basisKind'], index)
    return positions
def _prioritize(by_basis, unattributed, ranking):
    positions = _rank_positions(ranking)
    unranked_at = len(positions) + 1000
    ordered = sorted(
        by_basis.items(),
        key=lambda kv: (positions.get(
            kv[0], positions.get(kv[0].split(':')[0], unranked_at)),
            kv[0]))
    return {
        'prioritized': [{'basis': label, 'stances': entries}
                        for label, entries in ordered],
        # ANTI-DROWNING IS ORDERING, NEVER EXCLUSION: everything
        # unranked and unattributed still appears, after.
        'unattributed': unattributed,
        'orderingNote': 'relevance orders attention; no stance is '
                        'excluded by qualification',
    }
def prioritized_stances(manager, proof_name, context_name=''):
    """The by-basis proof reading, basis groups ORDERED by the
    context's voted relevance ranking. Default context: the proof's
    concept."""
    reading = proof_reading_by_basis(manager, proof_name)
    if not reading.get('ok'):
        return reading
    if not context_name:
        proof = _by_name(manager, 'TermProof').get(proof_name)
        context_name = getattr(proof, 'for_concept_name', '')
    relevance = qualification_relevance(manager, context_name)
    ordered = _prioritize(reading.get('byBasis', {}),
                          reading.get('unattributed', []),
                          relevance.get('ranking', []))
    return dict(reading, relevanceContext=context_name,
                relevanceRanking=relevance.get('ranking', []),
                **ordered)
def prioritized_assertion_stances(manager, assertion_name,
                                  context_name):
    reading = assertion_reading_by_basis(manager, assertion_name)
    if not reading.get('ok'):
        return reading
    relevance = qualification_relevance(manager, context_name)
    ordered = _prioritize(reading.get('byBasis', {}),
                          reading.get('unattributed', []),
                          relevance.get('ranking', []))
    return dict(reading, relevanceContext=context_name,
                relevanceRanking=relevance.get('ranking', []),
                **ordered)
def contributor_standing(manager, contributor_name, domain=''):
    """One person's claims (optionally filtered to a domain):
    kinds, qualifiers, attestation states, affiliations, conflicts,
    disputes — the accountability card."""
    claims = [c for c in _rows(manager, 'CredibilityClaim')
              if getattr(c, 'contributor_name', '')
              == contributor_name]
    if not claims:
        return {'ok': True, 'contributor': contributor_name,
                'claims': [],
                'note': 'no declared credibility claims — stances '
                        'read as unattributed basis (participation '
                        'is never gated on credentials)'}
    cards = []
    for claim in claims:
        covered = (_scope_covers(manager, claim, [domain])
                   if domain else None)
        if domain and covered is False:
            continue
        cards.append({
            'claim': claim.name,
            'basisKind': claim.basis_kind,
            'qualifier': claim.qualifier,
            'status': claim.status,
            'statement': claim.statement,
            'domainScope': json.loads(
                claim.domain_scope_json or '[]'),
            'affiliations': json.loads(
                claim.affiliations_json or '[]'),
            'declaredConflicts': json.loads(
                claim.declared_conflicts_json or '[]'),
            'independenceNote': claim.independence_note,
            'attestations': attestation_tally(manager, claim.name),
        })
    return {'ok': True, 'contributor': contributor_name,
            'domain': domain or None, 'claims': cards,
            'reading': _READING_NOTE}
