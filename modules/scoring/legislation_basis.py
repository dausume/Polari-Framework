"""
@module scoring.legislation_basis

Legislation tracking (Dustin 2026-07-16): WHO DRAFTED WHAT, WHO
VOTED yes/no when it went to a government vote, and WHAT LOBBIES OR
OTHER GROUPS CONTRIBUTED DIFFERENT PARTS of a bill — retrieved from
official public APIs where they exist (entry_mode 'api', source +
provenance attached) and hand-enterable where they do not
(entry_mode 'manual', the honest flag).

Provision-level attribution is the unit that makes "cramming things
where they do not belong" visible: each LegislationProvision carries
its OWN issue topic and its OWN contributor list, so a firearm
provision inside a highway bill is a row that says exactly that.
`detect_burial_patterns` finds two sequences:

  non-germane-provision   a provision whose issue clearly differs
                          from the bill's declared subject
  last-minute-insertion   a provision added within N days (knob) of
                          a floor vote

Findings are EVIDENCE-BEARING NARRATIVES ("provision §X addressing
<issue> sits in a bill declared about <subject>") — never verdicts
and never accusatory vocabulary; `file_burial_assertion` lands a
finding as a REAL scr-6 ScoreAssertion (status 'asserted') so the
validity-vote machinery adjudicates, not the detector.

@consumers
  - polariServer (registration, wired by the main session)
  - dmvdata.legis_sources_seed (the official-API registrations)
@see /political-scorecard-node/DEMOCRATIC_SCORECARD_REVAMP_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/legislation/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.assertions_basis import ScoreAssertion
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.legislation._shared import CONTRIBUTOR_KINDS, ENTRY_MODES, GERMANENESS_OVERLAP, KNOWN_LEGISLATURES, LAST_MINUTE_DAYS, LEGISLATION_STATUSES, VOTE_CHOICES, _STOP, _days_between, _germaneness, _insert, _persist, _topic_tokens, _validate_contributors, contributions_for, detect_burial_patterns, file_burial_assertion, legislator_voting_record, who_drafted, who_voted  # noqa: F401
from scoring.objects.legislation.LegislationRecord import LegislationRecord  # noqa: F401
from scoring.objects.legislation.LegislationProvision import LegislationProvision  # noqa: F401
from scoring.objects.legislation.LegislativeVoteEvent import LegislativeVoteEvent  # noqa: F401

from scoring.worldview_elections_basis import _by_name, _rows
import json

def enter_legislation(manager, payload):
    """The MANUAL entry act — validates, stamps entry_mode 'manual',
    refuses plainly."""
    name = payload.get('name', '')
    if not isinstance(name, str) or not name:
        return {'ok': False,
                'error': 'legislation needs a non-empty name'}
    if _by_name(manager, 'LegislationRecord').get(name) is not None:
        return {'ok': False,
                'error': f"legislation '{name}' already exists"}
    status = payload.get('status', 'introduced')
    if status not in LEGISLATION_STATUSES:
        return {'ok': False,
                'error': f'unknown status {status!r} (statuses: '
                         f'{", ".join(LEGISLATION_STATUSES)})'}
    drafted_by = payload.get('drafted_by', [])
    problem = _validate_contributors(drafted_by, 'drafted_by')
    if problem:
        return {'ok': False, 'error': problem}
    row = LegislationRecord(
        name=name, bill_id=payload.get('bill_id', ''),
        title=payload.get('title', ''),
        jurisdiction_subject_name=payload.get(
            'jurisdiction_subject_name', ''),
        legislature=payload.get('legislature', ''),
        status=status,
        declared_subject=payload.get('declared_subject', ''),
        text_url=payload.get('text_url', ''),
        drafted_by_json=json.dumps(drafted_by),
        entry_mode='manual',
        source_name=payload.get('source_name', ''),
        provenance_id=payload.get('provenance_id',
                                  'manual entry'),
        retrieved_at='', notes=payload.get('notes', ''),
        manager=manager)
    _insert(manager, 'LegislationRecord', row)
    return {'ok': True, 'legislation': name,
            'entryMode': 'manual'}
def enter_provision(manager, payload):
    legislation_name = payload.get('legislation_name', '')
    if _by_name(manager, 'LegislationRecord').get(
            legislation_name) is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    name = payload.get('name', '')
    if not name:
        return {'ok': False,
                'error': 'provision needs a non-empty name'}
    contributed_by = payload.get('contributed_by', [])
    problem = _validate_contributors(contributed_by,
                                     'contributed_by')
    if problem:
        return {'ok': False, 'error': problem}
    row = LegislationProvision(
        name=name, legislation_name=legislation_name,
        section_ref=payload.get('section_ref', ''),
        summary=payload.get('summary', ''),
        issue_name=payload.get('issue_name', ''),
        contributed_by_json=json.dumps(contributed_by),
        added_at=payload.get('added_at', ''),
        germane_note=payload.get('germane_note', ''),
        notes=payload.get('notes', ''), manager=manager)
    _insert(manager, 'LegislationProvision', row)
    return {'ok': True, 'provision': name}
def enter_vote_event(manager, payload):
    legislation_name = payload.get('legislation_name', '')
    if _by_name(manager, 'LegislationRecord').get(
            legislation_name) is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    name = payload.get('name', '')
    if not name:
        return {'ok': False,
                'error': 'vote event needs a non-empty name'}
    votes = payload.get('votes', {})
    if not isinstance(votes, dict):
        return {'ok': False,
                'error': "'votes' must be an object of "
                         '{legislator: yes|no|abstain|absent}'}
    bad_choices = {who: choice for who, choice in votes.items()
                   if choice not in VOTE_CHOICES}
    if bad_choices:
        return {'ok': False,
                'error': f'unknown vote choices: {bad_choices} '
                         f'(choices: {", ".join(VOTE_CHOICES)})'}
    known_subjects = set(_by_name(manager, 'ScoreSubject'))
    unknown = sorted(who for who in votes
                     if who not in known_subjects)
    row = LegislativeVoteEvent(
        name=name, legislation_name=legislation_name,
        chamber=payload.get('chamber', ''),
        occurred_at=payload.get('occurred_at', ''),
        result=payload.get('result', ''),
        vote_counts_json=json.dumps(payload.get('counts', {})),
        votes_json=json.dumps(votes),
        source_name=payload.get('source_name', ''),
        entry_mode='manual',
        provenance_id=payload.get('provenance_id', 'manual entry'),
        notes=payload.get('notes', ''), manager=manager)
    _insert(manager, 'LegislativeVoteEvent', row)
    result = {'ok': True, 'voteEvent': name,
              'entryMode': 'manual'}
    if unknown:
        # A suggestion, not a refusal: the roster is recorded as
        # entered; unknown names likely need ScoreSubject rows.
        result['suggestion'] = {
            'knob': 'ScoreSubject',
            'action': f'legislators {unknown} are not ScoreSubject '
                      f'rows — create them (kind politician) or fix '
                      f'the names so voting records aggregate'}
    return result
