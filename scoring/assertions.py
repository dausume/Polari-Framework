"""
@cross-cutting
@module scoring.assertions
@tags @xc:bindings

ScoreAssertion + AssertionValidityVote (scr-5) — the seam that binds
POLICY TEXT to score concepts. Dustin 2026-07-08: "based on
highlighting and assertion that portions of policy impact a particular
concept … assign scores via assertions of generic intents and then
suggestions of scores that should apply".

Typed assertions (the scorecard's legislativecompetition README,
adopted):
  score-impact — a span supports/harms a concept or term.
  dependency   — score carry-over from another policy subject this
                 one depends on (a nested edge between policies).
  decorative   — a span asserted to carry NO score weight (preambles,
                 boilerplate) — exclusion is itself an assertion.

Lifecycle: asserted → under-review → confirmed | rejected (re-open to
under-review allowed). Every transition APPENDS to
status_history_json — accountability can't be quietly rewritten.
Multi-round validity VOTING (the scorecard's designed rounds) tallies
through the same AgreementPolicy bands as group agreement; the tally
SUGGESTS a transition, never applies one (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.policy_scoring / scoring.abstraction / scoring.scoring_api
@see /OVERLAP_MAP.md
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy import classify_max, policy_bands

ASSERTION_TYPES = ('score-impact', 'dependency', 'decorative')
DIRECTIONS = ('supports', 'harms')
STATUSES = ('asserted', 'under-review', 'confirmed', 'rejected')

#: Allowed lifecycle moves — confirmed/rejected may be RE-OPENED (to
#: under-review), never silently flipped; history keeps every move.
ALLOWED_TRANSITIONS = {
    'asserted': ('under-review', 'confirmed', 'rejected'),
    'under-review': ('confirmed', 'rejected'),
    'confirmed': ('under-review',),
    'rejected': ('under-review',),
}


class ScoreAssertion(treeObject):
    """One claim binding a target (usually a policy text span) to a
    score concept/term."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('assert-fair-wage-min-wage').
        name: str = '',
        display_name: str = '',
        # ScoreSubject this assertion is ABOUT (policies are
        # subjects). The score-bearing anchor.
        subject_name: str = '',
        # Optional objectRef into any Polari object the assertion
        # targets (a legislation row, a ruling…).
        target_ref_json: str = '',
        # Optional text span (JSON {'start','end','quote'}) — the
        # scorecard's W3C-annotation idiom generalized. The quote
        # travels so the claim stays readable without the source.
        span_json: str = '',
        # The generic intent, free text ('raises minimum wage for
        # hourly workers') — what abstraction matching reads.
        intent: str = '',
        # ASSERTION_TYPES entry.
        assertion_type: str = 'score-impact',
        # DIRECTIONS entry (score-impact/dependency only).
        direction: str = 'supports',
        # How strongly the span bears on the concept (0-1).
        strength: float = 0.5,
        # The binding — may be EMPTY (suggestions fill it): concept
        # OR term of the concept being asserted about.
        concept_name: str = '',
        term_name: str = '',
        # dependency type: the policy subject scores carry over FROM.
        depends_on_subject: str = '',
        # MediaEvidence names cited as proof (JSON list).
        evidence_names_json: str = '[]',
        # Contributor name — who is accountable for this claim.
        asserted_by: str = '',
        # STATUSES entry; move via transition_assertion (history).
        status: str = 'asserted',
        # Append-only transition log (JSON list of {'from','to','by',
        # 'note','at'}) — tamper-evident lite.
        status_history_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.subject_name = subject_name
        self.target_ref_json = target_ref_json
        self.span_json = span_json
        self.intent = intent
        self.assertion_type = assertion_type
        self.direction = direction
        self.strength = strength
        self.concept_name = concept_name
        self.term_name = term_name
        self.depends_on_subject = depends_on_subject
        self.evidence_names_json = evidence_names_json
        self.asserted_by = asserted_by
        self.status = status
        self.status_history_json = status_history_json
        self.provenance_id = provenance_id
        self.notes = notes


class AssertionValidityVote(treeObject):
    """One contributor's vote, in one round, on one assertion's
    validity (the scorecard's multi-round design)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        assertion_name: str = '',
        # Contributor name — votes are accountable too.
        voter: str = '',
        round_number: int = 1,
        # 'valid' | 'invalid' | 'abstain'.
        vote: str = 'abstain',
        rationale: str = '',
        # Optional counter-/supporting evidence (JSON name list).
        evidence_names_json: str = '[]',
        cast_date: str = '',
        manager=None,
    ):
        self.name = name
        self.assertion_name = assertion_name
        self.voter = voter
        self.round_number = round_number
        self.vote = vote
        self.rationale = rationale
        self.evidence_names_json = evidence_names_json
        self.cast_date = cast_date


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
