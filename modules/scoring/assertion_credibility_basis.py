"""
@cross-cutting
@module scoring.assertion_credibility_basis
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
lifecycle path. The reading mirrors dmvdata.cross_validation_basis's
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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/assertion_credibility/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.survival_costs_basis import SMALL_SAMPLE

from scoring.objects.assertion_credibility._shared import CREDIBILITY_LEVELS, CREDIBILITY_PRIOR, CREDIBILITY_WEIGHTS, _by_name, _persist, _rows, _unit_key, assertion_credibility_reading  # noqa: F401
from scoring.objects.assertion_credibility.AssertionCredibilityVote import AssertionCredibilityVote  # noqa: F401

from datetime import datetime, timezone

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
