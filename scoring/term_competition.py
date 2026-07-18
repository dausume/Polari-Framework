"""
@cross-cutting
@module scoring.term_competition
@tags @xc:bindings

Term Competition — the PSC termcompetition draft (Java README:
'term scope' = the valid terms for a Score's scientific context;
'purpose-equivalent terms' compete within that scope), finally built
in Polari (Dustin 2026-07-16):

  TermProposal          — a group's composite/computed term candidacy
                          for a Score, every composition entry CITED
                          to a specific source (uncited refused).
  TermRelationAssertion — asserted logical relations between terms:
                          logical-equivalent / purpose-equivalent /
                          logical-subset (related incorporated into
                          subject) / logically-exclusive-competing
                          ("this should be considered logically
                          identical/exclusive to another term — they
                          are competing terms for legitimacy") /
                          other. Confirmed relations may be
                          MATERIALIZED into ScoreTerm's long-dormant
                          equivalent_terms_json /
                          competitive_terms_json — suggestion first,
                          apply explicitly, never silent.
  context_fit           — validate a term is at least a closest match
                          to the Score's context: topic, time,
                          location (parent-chain aware), whatever
                          context kinds are declared.
  TermScopeVote         — vote on which terms even MEET CRITERIA for
                          consideration (the 'term scope' gate);
                          verdicts flip proposal status only through
                          an explicit act.
  legitimacy elections  — voting-based competitions for which
                          in-scope terms are most legitimate, riding
                          the EXISTING WorldviewElection machinery
                          (approval/sole/ranked-condorcet) at group
                          scale AND global scale. Applying an
                          election marks the winner 'elected' and
                          returns the concept-weight change as a
                          SUGGESTION — the concept row is the knob,
                          never auto-edited.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (future term-competition endpoints)
@see /OVERLAP_MAP.md
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections import (ELECTION_MODES,
                                         WorldviewElection, _by_name,
                                         _parse, _rows, tally_election)

#: Proposal lifecycle. 'in-scope'/'excluded' flip ONLY through
#: apply_scope_verdict (an explicit act over the scope votes);
#: 'elected' only through apply_term_election.
PROPOSAL_STATUSES = ('proposed', 'in-scope', 'excluded', 'elected')

#: The relation vocabulary (directive verbatim in the module doc).
RELATION_KINDS = ('logical-equivalent', 'purpose-equivalent',
                  'logical-subset', 'logically-exclusive-competing',
                  'other')

#: Relation lifecycle mirrors scr-6 assertions (asserted →
#: under-review → confirmed | rejected; confirmed reopenable).
RELATION_STATUSES = ('asserted', 'under-review', 'confirmed',
                     'rejected')
RELATION_TRANSITIONS = {
    'asserted': ('under-review', 'confirmed', 'rejected'),
    'under-review': ('confirmed', 'rejected'),
    'confirmed': ('under-review',),
    'rejected': ('under-review',),
}

#: Which confirmed relations materialize into which dormant
#: ScoreTerm field. logical-subset and 'other' stay assertion-level
#: (reported by relations_for, never folded into either list —
#: incorporation is not equivalence, and 'other' is not a claim the
#: engine should act on).
_MATERIALIZE_FIELD = {
    'logical-equivalent': 'equivalent_terms_json',
    'purpose-equivalent': 'equivalent_terms_json',
    'logically-exclusive-competing': 'competitive_terms_json',
}

#: Below this many distinct voting units a scope tally is a hint
#: (scr-12a precedent).
SMALL_SAMPLE = 5

_ELECTION_PREFIX = 'term-election--'
_ELECTION_SCALES = ('group', 'global')


class TermProposal(treeObject):
    """One group's composite/computed term, in consideration for one
    Score (concept)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('quality-adjusted-rent--housing-price-tenants').
        name: str = '',
        # The ScoreTerm being proposed (new or existing row).
        proposed_term_name: str = '',
        # The Score under consideration.
        for_concept_name: str = '',
        proposed_by_group: str = '',
        proposed_by: str = '',
        # How the term is computed, every entry CITED:
        # [{"sourceTerm"|"sourceName": ..., "operation": ...,
        #   "source_name": <registered source>, "citation_url": ...,
        #   "note": ...}, ...]
        composition_json: str = '[]',
        rationale: str = '',
        # PROPOSAL_STATUSES entry.
        status: str = 'proposed',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.proposed_term_name = proposed_term_name
        self.for_concept_name = for_concept_name
        self.proposed_by_group = proposed_by_group
        self.proposed_by = proposed_by
        self.composition_json = composition_json
        self.rationale = rationale
        self.status = status
        self.notes = notes


class TermRelationAssertion(treeObject):
    """One asserted logical relation between two terms."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject_term: str = '',
        related_term: str = '',
        # RELATION_KINDS entry. 'logical-subset' means related_term
        # is INCORPORATED INTO subject_term.
        relation: str = '',
        asserted_by: str = '',
        on_behalf_of_group: str = '',
        rationale: str = '',
        evidence_url: str = '',
        # RELATION_STATUSES entry + append-only history.
        status: str = 'asserted',
        status_history_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_term = subject_term
        self.related_term = related_term
        self.relation = relation
        self.asserted_by = asserted_by
        self.on_behalf_of_group = on_behalf_of_group
        self.rationale = rationale
        self.evidence_url = evidence_url
        self.status = status
        self.status_history_json = status_history_json
        self.notes = notes


class TermScopeVote(treeObject):
    """One voting unit's stance on whether a term MEETS CRITERIA for
    consideration in a Score's term scope."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        concept_name: str = '',
        term_name: str = '',
        voter: str = '',
        # '' = the voter acts as an individual unit.
        on_behalf_of_group: str = '',
        eligible: bool = True,
        rationale: str = '',
        cast_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.concept_name = concept_name
        self.term_name = term_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.eligible = eligible
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes


def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory managers (selftests) have no db


def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row


# --------------------------------------------------------------- #
# 1. Proposals (composite/computed terms from CITED sources)
# --------------------------------------------------------------- #

def propose_term(manager, name, proposed_term_name, for_concept_name,
                 proposed_by_group, proposed_by, composition,
                 rationale='', notes=''):
    """A group puts a composite/computed term in consideration for a
    Score. Every composition entry must cite its source — uncited
    compositions are refused (credibility starts at the citation)."""
    if _by_name(manager, 'TermProposal').get(name) is not None:
        return {'ok': False,
                'error': f"a TermProposal named '{name}' already "
                         'exists'}
    if _by_name(manager, 'ScoreConcept').get(
            for_concept_name) is None:
        return {'ok': False,
                'error': f"no ScoreConcept named "
                         f"'{for_concept_name}'",
                'knownConcepts': sorted(
                    _by_name(manager, 'ScoreConcept'))}
    if not isinstance(composition, list) or not composition:
        return {'ok': False,
                'error': 'composition must be a non-empty list of '
                         'cited entries'}
    uncited = [i for i, entry in enumerate(composition)
               if not isinstance(entry, dict)
               or not entry.get('source_name')
               or not entry.get('citation_url')]
    if uncited:
        return {'ok': False,
                'error': f'composition entries {uncited} lack '
                         f"'source_name' + 'citation_url' — "
                         'composite terms must be computed from '
                         'SPECIFIC CITED data sources',
                'suggestion': {
                    'knob': 'composition_json',
                    'action': 'cite each entry (source_name = a '
                              'registered source row, citation_url '
                              '= the specific product/table)'}}
    row = TermProposal(
        name=name, proposed_term_name=proposed_term_name,
        for_concept_name=for_concept_name,
        proposed_by_group=proposed_by_group,
        proposed_by=proposed_by,
        composition_json=json.dumps(composition),
        rationale=rationale, status='proposed', notes=notes,
        manager=manager)
    _insert(manager, 'TermProposal', row)
    return {'ok': True, 'proposal': name, 'status': 'proposed'}


def proposals_for(manager, concept_name, statuses=None):
    wanted = set(statuses or PROPOSAL_STATUSES)
    return [p for p in _rows(manager, 'TermProposal')
            if getattr(p, 'for_concept_name', '') == concept_name
            and getattr(p, 'status', '') in wanted]


# --------------------------------------------------------------- #
# 2. Relation assertions + materialization
# --------------------------------------------------------------- #

def assert_term_relation(manager, name, subject_term, related_term,
                         relation, asserted_by,
                         on_behalf_of_group='', rationale='',
                         evidence_url='', notes=''):
    if relation not in RELATION_KINDS:
        return {'ok': False,
                'error': f"unknown relation '{relation}'",
                'relations': list(RELATION_KINDS)}
    if subject_term == related_term:
        return {'ok': False,
                'error': 'a term cannot relate to itself'}
    if not (rationale or '').strip():
        return {'ok': False,
                'error': 'a relation assertion needs a rationale — '
                         'the claim is contestable content, not a '
                         'label'}
    if relation == 'other' and not (notes or '').strip():
        return {'ok': False,
                'error': "relation 'other' requires notes describing "
                         'the logical consideration'}
    if _by_name(manager, 'TermRelationAssertion').get(
            name) is not None:
        return {'ok': False,
                'error': f"a TermRelationAssertion named '{name}' "
                         'already exists'}
    row = TermRelationAssertion(
        name=name, subject_term=subject_term,
        related_term=related_term, relation=relation,
        asserted_by=asserted_by,
        on_behalf_of_group=on_behalf_of_group,
        rationale=rationale, evidence_url=evidence_url,
        status='asserted', status_history_json='[]', notes=notes,
        manager=manager)
    _insert(manager, 'TermRelationAssertion', row)
    return {'ok': True, 'relation': name, 'status': 'asserted'}


def transition_term_relation(manager, name, to_status, by='',
                             note=''):
    """scr-6-style lifecycle move with append-only history."""
    row = _by_name(manager, 'TermRelationAssertion').get(name)
    if row is None:
        return {'ok': False,
                'error': f"no TermRelationAssertion named '{name}'"}
    if to_status not in RELATION_STATUSES:
        return {'ok': False,
                'error': f"unknown status '{to_status}'",
                'statuses': list(RELATION_STATUSES)}
    current = getattr(row, 'status', 'asserted')
    if to_status not in RELATION_TRANSITIONS.get(current, ()):
        return {'ok': False,
                'error': f"transition '{current}' → '{to_status}' "
                         'not allowed',
                'allowedFrom': list(
                    RELATION_TRANSITIONS.get(current, ()))}
    history = _parse(getattr(row, 'status_history_json', '[]'), '[]')
    history.append({'from': current, 'to': to_status, 'by': by,
                    'note': note,
                    'at': datetime.now(timezone.utc).isoformat(
                        timespec='seconds')})
    row.status = to_status
    row.status_history_json = json.dumps(history)
    _persist(manager, row)
    return {'ok': True, 'relation': name, 'status': to_status}


def relations_for(manager, term_name, statuses=None):
    """Every relation touching a term, both directions."""
    wanted = set(statuses or RELATION_STATUSES)
    out = []
    for r in _rows(manager, 'TermRelationAssertion'):
        if getattr(r, 'status', '') not in wanted:
            continue
        if getattr(r, 'subject_term', '') == term_name:
            out.append({'name': r.name, 'direction': 'subject',
                        'otherTerm': r.related_term,
                        'relation': r.relation, 'status': r.status,
                        'rationale': r.rationale})
        elif getattr(r, 'related_term', '') == term_name:
            out.append({'name': r.name, 'direction': 'related',
                        'otherTerm': r.subject_term,
                        'relation': r.relation, 'status': r.status,
                        'rationale': r.rationale})
    return out


def materialize_confirmed_relations(manager, term_name, apply=False):
    """Fold CONFIRMED relations into the term row's long-dormant
    equivalent_terms_json / competitive_terms_json. apply=False
    (default) returns the proposed additions as a SUGGESTION;
    apply=True writes them — an explicit act, never silent."""
    term = _by_name(manager, 'ScoreTerm').get(term_name)
    if term is None:
        return {'ok': False,
                'error': f"no ScoreTerm named '{term_name}'"}
    additions = {'equivalent_terms_json': [],
                 'competitive_terms_json': []}
    skipped = []
    for rel in relations_for(manager, term_name,
                             statuses=['confirmed']):
        field = _MATERIALIZE_FIELD.get(rel['relation'])
        if field is None:
            skipped.append({'relation': rel['name'],
                            'kind': rel['relation'],
                            'why': 'assertion-level only '
                                   '(incorporation/other is not '
                                   'equivalence)'})
            continue
        additions[field].append(rel['otherTerm'])
    proposed = {}
    for field, names in additions.items():
        current = _parse(getattr(term, field, '[]'), '[]')
        new = sorted(set(names) - set(current))
        if new:
            proposed[field] = {'current': current, 'add': new}
    result = {'ok': True, 'term': term_name, 'applied': apply,
              'proposed': proposed, 'skipped': skipped,
              'suggestion': {
                  'knob': f'ScoreTerm.{"/".join(proposed) or "…"} '
                          f'({term_name})',
                  'action': 'call with apply=True to fold the '
                            'confirmed relations into the term row'}
              if proposed and not apply else None}
    if apply and proposed:
        for field, change in proposed.items():
            setattr(term, field,
                    json.dumps(change['current'] + change['add']))
        _persist(manager, term)
    return result


# --------------------------------------------------------------- #
# 3. Context fit ("at least a closest match to the context of the
#    score being considered")
# --------------------------------------------------------------- #

def _tokenize(text):
    return {t for t in
            ''.join(c if c.isalnum() else ' '
                    for c in (text or '').lower()).split()
            if len(t) > 2}


def _ancestors(manager, context_name):
    """Parent chain of a ScoreContext (location hierarchies etc.)."""
    contexts = _by_name(manager, 'ScoreContext')
    chain, current = [], contexts.get(context_name)
    seen = set()
    while current is not None:
        parent = getattr(current, 'parent_name', '')
        if not parent or parent in seen:
            break
        seen.add(parent)
        chain.append(parent)
        current = contexts.get(parent)
    return chain


def _dimension_match(manager, required_name, term_context_names):
    """How well a term's measured contexts satisfy ONE required
    context: exact 1.0; term context is a DESCENDANT of the required
    (more specific data inside the required scope) 0.8; ANCESTOR
    (less specific) 0.5; token overlap for non-hierarchical kinds."""
    if required_name in term_context_names:
        return 1.0, f"exact context match '{required_name}'"
    contexts = _by_name(manager, 'ScoreContext')
    required = contexts.get(required_name)
    best, evidence = 0.0, f"no context matches '{required_name}'"
    for tc in term_context_names:
        if required_name in _ancestors(manager, tc):
            if 0.8 > best:
                best, evidence = 0.8, (
                    f"'{tc}' lies inside '{required_name}' "
                    '(descendant — more specific data)')
            continue
        if tc in _ancestors(manager, required_name):
            if 0.5 > best:
                best, evidence = 0.5, (
                    f"'{tc}' is an ancestor of '{required_name}' "
                    '(less specific data)')
            continue
        if required is not None:
            row = contexts.get(tc)
            same_kind = (row is not None
                         and getattr(row, 'context_type', '')
                         == getattr(required, 'context_type', ''))
            if same_kind:
                overlap = (_tokenize(tc) | _tokenize(
                    getattr(row, 'display_name', ''))) \
                    & (_tokenize(required_name) | _tokenize(
                        getattr(required, 'display_name', '')))
                score = min(0.4, 0.2 * len(overlap))
                if score > best:
                    best, evidence = score, (
                        f"'{tc}' shares tokens {sorted(overlap)} "
                        f"with '{required_name}'")
    return best, evidence


def context_fit(manager, term_name, concept_name):
    """Compare the contexts a term actually HAS values under against
    the Score's required contexts — topic, time, location, whatever
    kinds are declared. closestMatch ranks this term against the
    OTHER terms proposed for the same concept."""
    concept = _by_name(manager, 'ScoreConcept').get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'"}
    required = _parse(getattr(
        concept, 'required_context_names_json', '[]'), '[]')
    fit, dimensions, note = _fit_of(manager, term_name, required)
    if fit is None:
        return {'ok': False, 'term': term_name,
                'concept': concept_name, 'fit': None,
                'error': note,
                'suggestion': {
                    'knob': 'ContextualizedValue',
                    'action': f"ingest values for '{term_name}' "
                              'under the relevant contexts before '
                              'it can compete'}}
    rivals = {}
    for proposal in proposals_for(manager, concept_name):
        rival_term = getattr(proposal, 'proposed_term_name', '')
        if rival_term and rival_term != term_name:
            rival_fit, _, _ = _fit_of(manager, rival_term, required)
            rivals[rival_term] = rival_fit
    comparable = [v for v in rivals.values() if v is not None]
    closest = (None if not required else
               all(fit >= v for v in comparable))
    return {'ok': True, 'term': term_name, 'concept': concept_name,
            'fit': round(fit, 4), 'dimensions': dimensions,
            'closestMatch': closest,
            'rivalFits': {k: (round(v, 4) if v is not None else None)
                          for k, v in rivals.items()},
            'note': note}


def _fit_of(manager, term_name, required):
    values = [v for v in _rows(manager, 'ContextualizedValue')
              if getattr(v, 'term_name', '') == term_name]
    if not values:
        return None, [], (f"term '{term_name}' has NO "
                          'ContextualizedValues — unfit for '
                          'consideration until it carries data')
    term_contexts = set()
    for v in values:
        term_contexts.update(_parse(
            getattr(v, 'context_names_json', '[]'), '[]'))
    if not required:
        return 1.0, [], ('concept declares no required contexts — '
                         'every valued term fits trivially (declare '
                         'required_context_names_json to make the '
                         'scope meaningful)')
    dimensions = []
    total = 0.0
    for req in required:
        score, evidence = _dimension_match(manager, req,
                                           term_contexts)
        dimensions.append({'required': req, 'score': round(score, 4),
                           'evidence': evidence})
        total += score
    return total / len(required), dimensions, ''


# --------------------------------------------------------------- #
# 4. Scope eligibility votes
# --------------------------------------------------------------- #

def cast_scope_vote(manager, name, concept_name, term_name, voter,
                    eligible, on_behalf_of_group='', rationale='',
                    cast_at=''):
    if not voter:
        return {'ok': False,
                'error': 'scope votes are accountable — voter '
                         'required (pseudonyms ok)'}
    row = TermScopeVote(
        name=name, concept_name=concept_name, term_name=term_name,
        voter=voter, on_behalf_of_group=on_behalf_of_group,
        eligible=bool(eligible), rationale=rationale,
        cast_at=cast_at or datetime.now(timezone.utc).isoformat(
            timespec='seconds'),
        manager=manager)
    _insert(manager, 'TermScopeVote', row)
    return {'ok': True, 'vote': name}


def scope_tally(manager, concept_name, term_name):
    """Distinct voting units (a group counts once; an individual
    without a group counts as their own unit); each unit's LATEST
    vote supersedes its earlier ones."""
    votes = sorted(
        (v for v in _rows(manager, 'TermScopeVote')
         if getattr(v, 'concept_name', '') == concept_name
         and getattr(v, 'term_name', '') == term_name),
        key=lambda v: getattr(v, 'cast_at', ''))
    latest = {}
    for v in votes:
        unit = (getattr(v, 'on_behalf_of_group', '')
                or f"individual:{getattr(v, 'voter', '')}")
        latest[unit] = v
    eligible = sorted(u for u, v in latest.items() if v.eligible)
    ineligible = sorted(u for u, v in latest.items()
                        if not v.eligible)
    total = len(latest)
    verdict = ('no-votes' if total == 0 else
               'eligible' if len(eligible) > len(ineligible) else
               'ineligible' if len(ineligible) > len(eligible) else
               'tied')
    return {'ok': True, 'concept': concept_name, 'term': term_name,
            'units': total, 'eligibleUnits': eligible,
            'ineligibleUnits': ineligible, 'verdict': verdict,
            'smallSample': 0 < total < SMALL_SAMPLE,
            'note': 'a unit = a group, or an ungrouped individual; '
                    "each unit's latest vote counts"}


def apply_scope_verdict(manager, concept_name, term_name):
    """THE EXPLICIT ACT that flips proposal status from the scope
    tally — never automatic on vote cast."""
    tally = scope_tally(manager, concept_name, term_name)
    proposals = [p for p in proposals_for(manager, concept_name)
                 if getattr(p, 'proposed_term_name', '') == term_name]
    if not proposals:
        return {'ok': False,
                'error': f"no TermProposal proposes '{term_name}' "
                         f"for '{concept_name}'"}
    if tally['verdict'] == 'no-votes':
        return {'ok': False, 'error': 'no scope votes cast',
                'suggestion': {'knob': 'TermScopeVote',
                               'action': 'cast_scope_vote first'}}
    if tally['verdict'] == 'tied':
        return {'ok': False,
                'error': 'scope vote is tied — no verdict to apply',
                'tally': tally}
    new_status = ('in-scope' if tally['verdict'] == 'eligible'
                  else 'excluded')
    flipped = []
    for p in proposals:
        if getattr(p, 'status', '') == 'elected':
            return {'ok': False,
                    'error': f"proposal '{p.name}' is already "
                             "'elected' — an elected term's scope "
                             'is re-contested via a new election, '
                             'not a scope flip'}
        p.status = new_status
        _persist(manager, p)
        flipped.append(p.name)
    return {'ok': True, 'status': new_status, 'proposals': flipped,
            'tally': tally,
            'smallSample': tally['smallSample']}


# --------------------------------------------------------------- #
# 5. Legitimacy elections (riding WorldviewElection unchanged)
# --------------------------------------------------------------- #

def open_term_election(manager, concept_name, scale, group_name='',
                       mode='approval', name=None):
    """A voting-based competition over the concept's IN-SCOPE term
    proposals. scale 'group' = one group's internal competition;
    'global' = all scales, open electorate. Candidates are PROPOSAL
    names (traceable to group + term); the rows are plain
    WorldviewElections, so the existing tally machinery applies
    unchanged (the name prefix + notes carry the term-competition
    kind honestly — WorldviewElection has no kind field)."""
    if scale not in _ELECTION_SCALES:
        return {'ok': False, 'error': f"unknown scale '{scale}'",
                'scales': list(_ELECTION_SCALES)}
    if mode not in ELECTION_MODES:
        return {'ok': False, 'error': f"unknown mode '{mode}'",
                'modes': list(ELECTION_MODES)}
    if scale == 'group':
        if not group_name:
            return {'ok': False,
                    'error': "scale 'group' requires group_name"}
        if _by_name(manager, 'ScoreGroup').get(group_name) is None:
            return {'ok': False,
                    'error': f"no ScoreGroup named '{group_name}'"}
    elif group_name:
        return {'ok': False,
                'error': "scale 'global' takes no group_name — the "
                         'electorate is open'}
    in_scope = proposals_for(manager, concept_name,
                             statuses=['in-scope'])
    if not in_scope:
        return {'ok': False,
                'error': f"no in-scope proposals for "
                         f"'{concept_name}' — nothing to compete",
                'suggestion': {
                    'knob': 'TermScopeVote + apply_scope_verdict',
                    'action': 'vote terms into scope first (the '
                              'term-scope gate precedes legitimacy)'}}
    election_name = name or (
        f'{_ELECTION_PREFIX}{concept_name}--{scale}'
        + (f'--{group_name}' if group_name else ''))
    if _by_name(manager, 'WorldviewElection').get(
            election_name) is not None:
        return {'ok': False,
                'error': f"election '{election_name}' already exists"}
    row = WorldviewElection(
        name=election_name,
        display_name=f'Term legitimacy: {concept_name} ({scale})',
        description='Term-competition legitimacy election — '
                    'candidates are TermProposal names.',
        group_name=group_name,
        candidate_concept_names_json=json.dumps(
            sorted(p.name for p in in_scope)),
        mode=mode, status='open',
        notes=f'term-legitimacy-election concept={concept_name} '
              f'scale={scale}',
        manager=manager)
    _insert(manager, 'WorldviewElection', row)
    return {'ok': True, 'election': election_name,
            'candidates': sorted(p.name for p in in_scope),
            'scale': scale, 'mode': mode}


def apply_term_election(manager, election_name):
    """Tally a CLOSED legitimacy election: the winning proposal is
    marked 'elected'; the concept's term-weight change comes back as
    a SUGGESTION ONLY — the ScoreConcept row is the knob and is
    never auto-edited."""
    election = _by_name(manager, 'WorldviewElection').get(
        election_name)
    if election is None or not election_name.startswith(
            _ELECTION_PREFIX):
        return {'ok': False,
                'error': f"'{election_name}' is not a term-"
                         'legitimacy election',
                'knownTermElections': sorted(
                    n for n in _by_name(manager, 'WorldviewElection')
                    if n.startswith(_ELECTION_PREFIX))}
    tally = tally_election(manager, election_name)
    if not tally.get('ok'):
        return tally
    if tally['status'] != 'closed':
        return {'ok': False,
                'error': f"election '{election_name}' is "
                         f"'{tally['status']}' — only closed "
                         'elections apply (results that can still '
                         'change never silently elect a term)',
                'suggestion': {
                    'knob': 'WorldviewElection.status',
                    'action': "set 'closed' first (an explicit "
                              'edit)'}}
    proposals = _by_name(manager, 'TermProposal')
    winners = tally['winners']
    elected = None
    if len(winners) == 1:
        winner = proposals.get(winners[0])
        if winner is not None:
            winner.status = 'elected'
            _persist(manager, winner)
            elected = winner.name
    weight_suggestion = {}
    for proposal_name, weight in tally['electedWeights'].items():
        proposal = proposals.get(proposal_name)
        if proposal is not None and weight > 0:
            weight_suggestion[
                getattr(proposal, 'proposed_term_name', '')] = weight
    concept_name = ''
    for part in (getattr(election, 'notes', '') or '').split():
        if part.startswith('concept='):
            concept_name = part[len('concept='):]
    return {'ok': True, 'election': election_name,
            'winners': winners, 'elected': elected,
            'note': (None if elected else
                     'tied winners — no proposal marked elected; '
                     'break the tie with a runoff election'),
            'suggestion': {
                'knob': f'ScoreConcept.term_weights_json '
                        f'({concept_name})',
                'proposedWeights': weight_suggestion,
                'action': 'apply these vote-derived term weights to '
                          'the concept row explicitly — the concept '
                          'is the knob, this election only suggests'}}


# --------------------------------------------------------------- #
# 6. The full-flow report
# --------------------------------------------------------------- #

def term_competition_report(manager, concept_name):
    concept = _by_name(manager, 'ScoreConcept').get(concept_name)
    if concept is None:
        return {'ok': False,
                'error': f"no ScoreConcept named '{concept_name}'"}
    proposals = []
    for p in proposals_for(manager, concept_name):
        term = getattr(p, 'proposed_term_name', '')
        fit = context_fit(manager, term, concept_name)
        proposals.append({
            'proposal': p.name, 'term': term,
            'group': getattr(p, 'proposed_by_group', ''),
            'status': getattr(p, 'status', ''),
            'composition': _parse(
                getattr(p, 'composition_json', '[]'), '[]'),
            'contextFit': (fit.get('fit')
                           if fit.get('ok') else None),
            'closestMatch': fit.get('closestMatch'),
            'relations': relations_for(manager, term),
            'scopeTally': scope_tally(manager, concept_name, term),
        })
    elections = []
    for name, election in _by_name(
            manager, 'WorldviewElection').items():
        if name.startswith(_ELECTION_PREFIX) and \
                f'concept={concept_name}' in (
                    getattr(election, 'notes', '') or ''):
            elections.append({
                'election': name,
                'status': getattr(election, 'status', ''),
                'mode': getattr(election, 'mode', ''),
                'tally': tally_election(manager, name)})
    return {'ok': True, 'concept': concept_name,
            'termScopeNote': 'term scope = the terms voted eligible '
                             "for this Score's context "
                             '(termcompetition draft, built)',
            'proposals': proposals, 'elections': elections}
