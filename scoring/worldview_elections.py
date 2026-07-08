"""
@cross-cutting
@module scoring.worldview_elections
@tags @xc:bindings

Worldview elections (scr-8) — the scorecard's designed-never-built
WorldviewVote (approval / sole / ranked-condorcet), tallied in
Polari. Election close → tally → a ScoreGroup's member worldviews
get VOTE-DERIVED weights instead of hand-set ones (the weights feed
group aggregation, so an elected definition is what the group
actually reads by).

Honesty rules:
  - Tallying an OPEN election is fine (a running count); APPLYING
    one refuses — results that can still change never silently
    become the group's definition. Close first (an explicit edit).
  - Malformed ballots are refused BY NAME, never guessed.
  - Ranked mode seeks a Condorcet winner; when none exists the
    Copeland fallback is LABELED, pairwise ties included.
  - Elected weights carry provenance onto the group row
    (weights_provenance) — weights without lineage are opinions.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (elections endpoints)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

ELECTION_MODES = ('approval', 'sole', 'ranked-condorcet')
ELECTION_STATUSES = ('open', 'closed')


class WorldviewElection(treeObject):
    """One election over candidate worldview concepts for a group."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The ScoreGroup whose member weights this election derives.
        group_name: str = '',
        # Candidate ScoreConcept names (JSON list); [] = the group's
        # member worldviews.
        candidate_concept_names_json: str = '[]',
        # ELECTION_MODES entry.
        mode: str = 'approval',
        # ELECTION_STATUSES entry — apply requires 'closed'.
        status: str = 'open',
        opens_date: str = '',
        closes_date: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.group_name = group_name
        self.candidate_concept_names_json = candidate_concept_names_json
        self.mode = mode
        self.status = status
        self.opens_date = opens_date
        self.closes_date = closes_date
        self.provenance_id = provenance_id
        self.notes = notes


class WorldviewBallot(treeObject):
    """One contributor's ballot in one election. Which payload field
    counts depends on the election's mode."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        election_name: str = '',
        # Contributor name — ballots are accountable (pseudonyms ok).
        voter: str = '',
        # approval mode: JSON list of approved candidate names.
        approvals_json: str = '[]',
        # sole mode: exactly one candidate name.
        sole_choice: str = '',
        # ranked-condorcet mode: JSON list, most-preferred first;
        # unranked candidates count below every ranked one.
        ranking_json: str = '[]',
        cast_date: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.election_name = election_name
        self.voter = voter
        self.approvals_json = approvals_json
        self.sole_choice = sole_choice
        self.ranking_json = ranking_json
        self.cast_date = cast_date
        self.notes = notes


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r for r in _rows(manager, class_name)}


def _parse(text, fallback):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _candidates(manager, election):
    explicit = _parse(getattr(
        election, 'candidate_concept_names_json', '[]'), '[]')
    if explicit:
        return explicit
    group = _by_name(manager, 'ScoreGroup').get(
        getattr(election, 'group_name', ''))
    if group is None:
        return []
    return _parse(
        getattr(group, 'member_concept_names_json', '[]'), '[]')


def _tally_approval(ballots, candidates):
    counts = {c: 0 for c in candidates}
    voters_per = {c: [] for c in candidates}
    refused = []
    for b in ballots:
        approvals = [a for a in _parse(
            getattr(b, 'approvals_json', '[]'), '[]')]
        valid = [a for a in approvals if a in counts]
        unknown = [a for a in approvals if a not in counts]
        if unknown:
            refused.append({'ballot': getattr(b, 'name', ''),
                            'error': f'unknown candidates {unknown}'})
            continue
        if not valid:
            refused.append({'ballot': getattr(b, 'name', ''),
                            'error': 'no approvals — an empty '
                                     'approval ballot says nothing'})
            continue
        for c in valid:
            counts[c] += 1
            voters_per[c].append(getattr(b, 'voter', ''))
    total = sum(counts.values())
    per = [{'candidate': c, 'approvals': counts[c],
            'voters': sorted(voters_per[c]),
            'share': round(counts[c] / total, 6) if total else 0.0}
           for c in candidates]
    per.sort(key=lambda p: -p['approvals'])
    top = max(counts.values()) if counts else 0
    winners = sorted(c for c, n in counts.items()
                     if n == top and top > 0)
    weights = {c: (counts[c] / total if total else 0.0)
               for c in candidates}
    return per, winners, weights, refused, \
        'weights = approval share (approvals ÷ total approvals)'


def _tally_sole(ballots, candidates):
    counts = {c: 0 for c in candidates}
    refused = []
    for b in ballots:
        choice = getattr(b, 'sole_choice', '') or ''
        if choice not in counts:
            refused.append({'ballot': getattr(b, 'name', ''),
                            'error': f"sole_choice '{choice}' is not "
                                     'a candidate'})
            continue
        counts[choice] += 1
    total = sum(counts.values())
    per = [{'candidate': c, 'votes': counts[c],
            'share': round(counts[c] / total, 6) if total else 0.0}
           for c in candidates]
    per.sort(key=lambda p: -p['votes'])
    top = max(counts.values()) if counts else 0
    winners = sorted(c for c, n in counts.items()
                     if n == top and top > 0)
    weights = {c: (counts[c] / total if total else 0.0)
               for c in candidates}
    return per, winners, weights, refused, \
        'weights = vote share (first-past counts ÷ ballots)'


def _tally_ranked(ballots, candidates):
    """Pairwise (Condorcet); unranked candidates count below every
    ranked one; Copeland fallback labeled when no Condorcet winner."""
    wins = {a: {b: 0 for b in candidates if b != a}
            for a in candidates}
    refused, counted = [], 0
    for b in ballots:
        ranking = [r for r in _parse(
            getattr(b, 'ranking_json', '[]'), '[]')]
        unknown = [r for r in ranking if r not in candidates]
        if unknown:
            refused.append({'ballot': getattr(b, 'name', ''),
                            'error': f'unknown candidates {unknown}'})
            continue
        if not ranking:
            refused.append({'ballot': getattr(b, 'name', ''),
                            'error': 'empty ranking'})
            continue
        counted += 1
        position = {c: i for i, c in enumerate(ranking)}
        for a in candidates:
            for c in candidates:
                if a == c:
                    continue
                a_pos = position.get(a)
                c_pos = position.get(c)
                if a_pos is not None and (c_pos is None
                                          or a_pos < c_pos):
                    wins[a][c] += 1
    pairwise, copeland = [], {c: 0 for c in candidates}
    for i, a in enumerate(candidates):
        for c in candidates[i + 1:]:
            a_wins, c_wins = wins[a][c], wins[c][a]
            if a_wins > c_wins:
                copeland[a] += 1
                beats = a
            elif c_wins > a_wins:
                copeland[c] += 1
                beats = c
            else:
                beats = None  # pairwise tie — no Copeland point
            pairwise.append({'pair': [a, c],
                             'wins': {a: a_wins, c: c_wins},
                             'beats': beats})
    n_others = len(candidates) - 1
    condorcet = sorted(c for c in candidates
                       if copeland[c] == n_others and n_others > 0)
    total_copeland = sum(copeland.values())
    weights = {c: (copeland[c] / total_copeland
                   if total_copeland else 0.0) for c in candidates}
    per = [{'candidate': c, 'copelandWins': copeland[c],
            'share': round(weights[c], 6)} for c in candidates]
    per.sort(key=lambda p: -p['copelandWins'])
    if condorcet:
        winners, method = condorcet, 'condorcet'
    else:
        top = max(copeland.values()) if copeland else 0
        winners = sorted(c for c, n in copeland.items() if n == top)
        method = 'copeland-fallback'
    note = ('weights = Copeland pairwise-win share; winner method: '
            f'{method}' + (' (no Condorcet winner — ties/cycles '
                           'present, labeled not hidden)'
                           if method == 'copeland-fallback' else ''))
    return per, winners, weights, refused, note, pairwise, counted


def tally_election(manager, election_name):
    """The running (or final) tally for one election — mode-specific
    counts, winner(s), derived weights, refused ballots by name."""
    election = _by_name(manager, 'WorldviewElection').get(
        election_name)
    if election is None:
        return {'ok': False,
                'error': f"no WorldviewElection named "
                         f"'{election_name}'",
                'knownElections': sorted(
                    _by_name(manager, 'WorldviewElection'))}
    mode = getattr(election, 'mode', 'approval')
    if mode not in ELECTION_MODES:
        return {'ok': False,
                'error': f"unknown mode '{mode}'",
                'modes': list(ELECTION_MODES)}
    candidates = _candidates(manager, election)
    if not candidates:
        return {'ok': False,
                'error': 'election has no candidates',
                'suggestion': {
                    'knob': 'candidate_concept_names_json / '
                            'group_name',
                    'action': 'list candidate worldviews, or point '
                              'group_name at a group with members'}}
    ballots = [b for b in _rows(manager, 'WorldviewBallot')
               if getattr(b, 'election_name', '') == election_name]
    if not ballots:
        return {'ok': False,
                'error': 'no ballots cast',
                'candidates': candidates}

    pairwise = None
    if mode == 'approval':
        per, winners, weights, refused, note = _tally_approval(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    elif mode == 'sole':
        per, winners, weights, refused, note = _tally_sole(
            ballots, candidates)
        counted = len(ballots) - len(refused)
    else:
        per, winners, weights, refused, note, pairwise, counted = \
            _tally_ranked(ballots, candidates)

    report = {
        'ok': True,
        'election': election_name,
        'displayName': getattr(election, 'display_name', '')
        or election_name,
        'group': getattr(election, 'group_name', ''),
        'mode': mode,
        'status': getattr(election, 'status', 'open'),
        'candidates': candidates,
        'ballotsCast': len(ballots),
        'ballotsCounted': counted,
        'refusedBallots': refused,
        'results': per,
        'winners': winners,
        'electedWeights': {c: round(w, 6)
                           for c, w in weights.items()},
        'note': note,
        'suggestion': {
            'knob': f'POST /api/scoring/elections/{election_name}'
                    '/apply',
            'action': "close the election (status = 'closed'), then "
                      "apply to write these weights onto the group "
                      '(explicit, provenance-stamped)'},
    }
    if pairwise is not None:
        report['pairwise'] = pairwise
    return report


def apply_election(manager, election_name):
    """Write a CLOSED election's elected weights onto its group
    (member_weights_json + weights_provenance). Applying an open
    election refuses — results that can still change never silently
    become the group's definition."""
    tally = tally_election(manager, election_name)
    if not tally.get('ok'):
        return tally
    if tally['status'] != 'closed':
        return {'ok': False,
                'error': f"election '{election_name}' is "
                         f"'{tally['status']}' — only closed "
                         'elections apply',
                'suggestion': {
                    'knob': 'WorldviewElection.status',
                    'action': "set 'closed' first (an explicit edit) "
                              'so the applied weights are final'}}
    group = _by_name(manager, 'ScoreGroup').get(tally['group'])
    if group is None:
        return {'ok': False,
                'error': f"election's group '{tally['group']}' does "
                         'not exist'}
    group.member_weights_json = json.dumps(tally['electedWeights'])
    group.weights_provenance = (
        f"vote-derived from election '{election_name}' "
        f"({tally['mode']}, {tally['ballotsCounted']} ballots "
        f"counted, winners: {', '.join(tally['winners']) or 'none'})")
    try:
        manager.db.saveInstanceInDB(group)
    except Exception:
        pass  # in-memory managers (selftests) have no db
    return {'ok': True,
            'election': election_name,
            'group': tally['group'],
            'appliedWeights': tally['electedWeights'],
            'weightsProvenance': group.weights_provenance,
            'note': 'group aggregation now reads members through '
                    'these weights — the elected definition is what '
                    'the group means'}


SEED_WORLDVIEW_ELECTIONS = [{
    'name': 'demo-labor-definition-election',
    'display_name': 'Town assembly: which labor worldview?',
    'description': 'Demo ranked-condorcet election over the four '
                   'member worldviews — carol wins every pairwise '
                   'matchup; apply writes vote-derived weights onto '
                   'the assembly group.',
    'group_name': 'demo-town-assembly',
    'mode': 'ranked-condorcet',
    'status': 'closed',
    'opens_date': '2024-05-01', 'closes_date': '2024-05-08',
    'provenance_id': 'scr-8 demo',
}]

SEED_WORLDVIEW_BALLOTS = [
    {
        'name': 'ballot-labor-def-jane',
        'election_name': 'demo-labor-definition-election',
        'voter': 'demo-citizen-jane',
        'ranking_json': json.dumps(
            ['member-labor-carol', 'member-labor-alice',
             'member-labor-bob', 'member-labor-dan']),
        'cast_date': '2024-05-02',
    },
    {
        'name': 'ballot-labor-def-research',
        'election_name': 'demo-labor-definition-election',
        'voter': 'demo-research-group',
        'ranking_json': json.dumps(
            ['member-labor-carol', 'member-labor-bob',
             'member-labor-alice', 'member-labor-dan']),
        'cast_date': '2024-05-03',
    },
    {
        'name': 'ballot-labor-def-lobby',
        'election_name': 'demo-labor-definition-election',
        'voter': 'demo-labor-lobby',
        'ranking_json': json.dumps(
            ['member-labor-alice', 'member-labor-bob',
             'member-labor-carol', 'member-labor-dan']),
        'cast_date': '2024-05-03',
    },
]

SEED_ASSEMBLY_GROUPS = [{
    'name': 'demo-town-assembly',
    'display_name': 'Demo Town Assembly',
    'group_type': 'civic',
    'member_concept_names_json': json.dumps(
        ['member-labor-alice', 'member-labor-bob',
         'member-labor-carol', 'member-labor-dan']),
    'member_contributor_names_json': json.dumps(
        ['demo-citizen-jane']),
    'description': 'All four demo worldviews — the scr-8 election '
                   'derives member weights for this group.',
}]
