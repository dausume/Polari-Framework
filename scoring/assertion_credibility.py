"""
@cross-cutting
@module scoring.assertion_credibility
@tags @xc:bindings

Assertion CREDIBILITY voting (Dustin 2026-07-16): "the capability for
groups, individuals, etc, to be able to vote on the credibility of an
assertion."

Relationship to scr-6 (documented so the two never fork): the
existing AssertionValidityVote rounds gate the assertion's STATUS
lifecycle (asserted → under-review → confirmed | rejected) — a
procedural adjudication. Credibility votes are the PARALLEL community
reading: how credible do groups and individuals find the claim,
weighted by distinct voices. Casting a credibility vote never moves
the status; tally_validity/transition_assertion remain the only
lifecycle path. The reading mirrors dmvdata.cross_validation's
sourcing_credibility precedent exactly: distinct units, latest vote
per unit, score bounded below 1 by construction, zero votes = unrated
(None) not zero, small samples flagged, and it is always "a
credibility READING with evidence, not a truth declaration".

Group stances: a group's official position is cast BY a member ON
BEHALF OF the group — the group is the counted unit (echoing members
add nothing), the caster is the accountability trail. ScoreGroup
membership is worldview-concept-based, not person-based, so the
caster is attribution rather than a checked roster — stated here
honestly rather than pretended.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (future credibility routes)
@see /OVERLAP_MAP.md
"""

import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.survival_costs import SMALL_SAMPLE

#: Three-level categorical, matching the house verdict idiom
#: (cross_validation's confirmed/partial/contradicted) — avoids the
#: false precision of a numeric slider and maps straight onto the
#: established weight formula.
CREDIBILITY_LEVELS = ('credible', 'questionable', 'not-credible')
CREDIBILITY_WEIGHTS = {'credible': 1.0, 'questionable': 0.5,
                       'not-credible': 0.0}
#: The +1 prior that keeps certainty unreachable (precedent:
#: cross_validation.CREDIBILITY_PRIOR).
CREDIBILITY_PRIOR = 1.0


class AssertionCredibilityVote(treeObject):
    """One credibility vote on one assertion — personal, or a
    group's official stance cast by a member. Rows are immutable;
    a re-vote is a NEW row and the reading takes each unit's latest
    (superseded rows stay visible — that IS the history)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('cred-assert-x--housing-guild-2').
        name: str = '',
        assertion_name: str = '',
        # Contributor name — every vote is accountable to a person.
        voter: str = '',
        # '' = personal vote; a ScoreGroup name = the group's
        # official stance (the GROUP is the counted unit).
        on_behalf_of_group: str = '',
        # CREDIBILITY_LEVELS entry.
        credibility: str = 'questionable',
        rationale: str = '',
        cited_evidence_url: str = '',
        cast_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.assertion_name = assertion_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.credibility = credibility
        self.rationale = rationale
        self.cited_evidence_url = cited_evidence_url
        self.cast_at = cast_at
        self.notes = notes


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


def cast_credibility_vote(manager, assertion_name, voter,
                          credibility, rationale='',
                          on_behalf_of_group='',
                          cited_evidence_url='', cast_at='',
                          name=''):
    """Cast (or re-cast) one unit's credibility vote. Honest
    refusals; returns which earlier vote of the same unit this one
    supersedes, if any."""
    if _by_name(manager, 'ScoreAssertion', assertion_name) is None:
        known = sorted(getattr(a, 'name', '')
                       for a in _rows(manager, 'ScoreAssertion'))
        return {'ok': False,
                'error': f"no ScoreAssertion named "
                         f"'{assertion_name}'",
                'knownAssertions': known}
    if credibility not in CREDIBILITY_LEVELS:
        return {'ok': False,
                'error': f"unknown credibility level "
                         f"'{credibility}'",
                'levels': list(CREDIBILITY_LEVELS)}
    if not voter:
        return {'ok': False,
                'error': 'votes are accountable — voter '
                         '(Contributor name) is required'}
    if _by_name(manager, 'Contributor', voter) is None:
        return {'ok': False,
                'error': f"no Contributor named '{voter}'",
                'suggestion': {
                    'knob': 'Contributor',
                    'action': 'register the voter as a Contributor '
                              'row first — accountability needs a '
                              'real identity'}}
    if on_behalf_of_group and _by_name(
            manager, 'ScoreGroup', on_behalf_of_group) is None:
        return {'ok': False,
                'error': f"no ScoreGroup named "
                         f"'{on_behalf_of_group}'",
                'suggestion': {
                    'knob': 'ScoreGroup',
                    'action': 'a group stance needs a real group '
                              'row; omit on_behalf_of_group for a '
                              'personal vote'}}
    cast_at = cast_at or datetime.now(timezone.utc).isoformat(
        timespec='seconds')
    existing_for_unit = [
        v for v in _rows(manager, 'AssertionCredibilityVote')
        if getattr(v, 'assertion_name', '') == assertion_name]
    unit = on_behalf_of_group or f'individual:{voter}'
    superseded = [getattr(v, 'name', '') for v in existing_for_unit
                  if _unit_key(v) == unit]
    if not name:
        name = (f'cred-{assertion_name}--'
                f'{unit.replace("individual:", "")}'
                f'-{len(superseded) + 1}')
    if _by_name(manager, 'AssertionCredibilityVote', name) is not None:
        return {'ok': False,
                'error': f"a credibility vote named '{name}' "
                         'already exists — pass a distinct name'}
    vote = AssertionCredibilityVote(
        name=name, assertion_name=assertion_name, voter=voter,
        on_behalf_of_group=on_behalf_of_group,
        credibility=credibility, rationale=rationale,
        cited_evidence_url=cited_evidence_url, cast_at=cast_at,
        manager=manager)
    table = manager.objectTables.setdefault(
        'AssertionCredibilityVote', {})
    if not any(existing is vote for existing in table.values()):
        table[name] = vote
    _persist(manager, vote)
    return {'ok': True, 'vote': name, 'unit': unit,
            'supersedes': superseded[-1] if superseded else None,
            'castAt': cast_at}


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
