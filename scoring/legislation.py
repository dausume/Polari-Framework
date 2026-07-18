"""
@module scoring.legislation

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
  - dmvdata.legis_sources (the official-API registrations)
@see /political-scorecard-node/DEMOCRATIC_SCORECARD_REVAMP_PLAN.md
"""

import json
from datetime import datetime

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.assertions import ScoreAssertion
from scoring.worldview_elections import _by_name, _rows

LEGISLATION_STATUSES = ('introduced', 'in-committee', 'passed',
                        'enacted', 'vetoed', 'failed')
#: Documented conventions; the field stays free text so new bodies
#: never need a code change.
KNOWN_LEGISLATURES = ('us-house', 'us-senate', 'dc-council',
                      'va-general-assembly', 'md-general-assembly')
CONTRIBUTOR_KINDS = ('legislator', 'staff', 'lobby', 'group',
                     'individual')
VOTE_CHOICES = ('yes', 'no', 'abstain', 'absent')
ENTRY_MODES = ('api', 'manual')

#: A provision added this close (days) to a floor vote is a
#: last-minute-insertion finding — a knob, not a verdict.
LAST_MINUTE_DAYS = 3
#: Token-overlap at or below this share reads as non-germane — a
#: knob; the narrative always quotes both topics so a human can
#: disagree with the threshold.
GERMANENESS_OVERLAP = 0.2


class LegislationRecord(treeObject):
    """One piece of legislation — API-retrieved or hand-entered,
    the entry_mode flag says which, honestly."""

    @treeObjectInit
    def __init__(self, name: str = '', bill_id: str = '',
                 title: str = '',
                 jurisdiction_subject_name: str = '',
                 legislature: str = '',
                 status: str = 'introduced',
                 # The bill's STATED topic — the germaneness
                 # baseline every provision is read against.
                 declared_subject: str = '',
                 text_url: str = '',
                 # WHO WROTE IT: JSON list of {kind, name,
                 # evidence_url} — multi-author by design.
                 drafted_by_json: str = '[]',
                 entry_mode: str = 'manual',
                 # GovSource / legal-source name it came from ('').
                 source_name: str = '',
                 provenance_id: str = '',
                 retrieved_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.bill_id = bill_id
        self.title = title
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.legislature = legislature
        self.status = status
        self.declared_subject = declared_subject
        self.text_url = text_url
        self.drafted_by_json = drafted_by_json
        self.entry_mode = entry_mode
        self.source_name = source_name
        self.provenance_id = provenance_id
        self.retrieved_at = retrieved_at
        self.notes = notes


class LegislationProvision(treeObject):
    """One part of a bill — the cram-visibility unit: its own topic,
    its own contributors."""

    @treeObjectInit
    def __init__(self, name: str = '', legislation_name: str = '',
                 section_ref: str = '',
                 summary: str = '',
                 # The topic THIS provision actually addresses.
                 issue_name: str = '',
                 # WHAT LOBBIES OR OTHER GROUPS CONTRIBUTED THIS
                 # PART: JSON list of {kind, name, evidence_url}.
                 contributed_by_json: str = '[]',
                 # '' = timing honestly unknown.
                 added_at: str = '',
                 germane_note: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.legislation_name = legislation_name
        self.section_ref = section_ref
        self.summary = summary
        self.issue_name = issue_name
        self.contributed_by_json = contributed_by_json
        self.added_at = added_at
        self.germane_note = germane_note
        self.notes = notes


class LegislativeVoteEvent(treeObject):
    """One government vote on one piece of legislation — the roster
    (who voted yes/no) travels with the tallies."""

    @treeObjectInit
    def __init__(self, name: str = '', legislation_name: str = '',
                 chamber: str = '', occurred_at: str = '',
                 result: str = '',
                 # {'yes': n, 'no': n, 'abstain': n, 'absent': n}
                 vote_counts_json: str = '{}',
                 # THE ROSTER: {legislator_subject_name: choice}.
                 votes_json: str = '{}',
                 source_name: str = '', entry_mode: str = 'manual',
                 provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.legislation_name = legislation_name
        self.chamber = chamber
        self.occurred_at = occurred_at
        self.result = result
        self.vote_counts_json = vote_counts_json
        self.votes_json = votes_json
        self.source_name = source_name
        self.entry_mode = entry_mode
        self.provenance_id = provenance_id
        self.notes = notes


def _persist(manager, row):
    db = getattr(manager, 'db', None)
    if db is None:
        return True
    try:
        db.saveInstanceInDB(row)
        return True
    except Exception as exc:
        print(f'[Legislation] DB save FAILED for '
              f'{getattr(row, "name", "?")}: {exc}', flush=True)
        return False


def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row


def _validate_contributors(entries, field):
    """The {kind, name} shape, kind from the documented set."""
    if not isinstance(entries, list):
        return f'{field} must be a list of {{kind, name}} entries'
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get('name'):
            return (f'{field} entries need at least a name — got '
                    f'{entry!r}')
        kind = entry.get('kind', '')
        if kind not in CONTRIBUTOR_KINDS:
            kinds = ', '.join(CONTRIBUTOR_KINDS)
            return (f"{field}: unknown contributor kind {kind!r} "
                    f'for {entry.get("name")!r} (kinds: {kinds})')
    return None


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


def who_drafted(manager, legislation_name):
    row = _by_name(manager, 'LegislationRecord').get(
        legislation_name)
    if row is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    return {'ok': True, 'legislation': legislation_name,
            'draftedBy': json.loads(row.drafted_by_json or '[]'),
            'entryMode': row.entry_mode,
            'source': row.source_name or None}


def who_voted(manager, legislation_name):
    """Roster + tallies per vote event, with the counts-vs-roster
    reconciliation — a mismatch is an honest warning, never
    silently preferred either way."""
    if _by_name(manager, 'LegislationRecord').get(
            legislation_name) is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    events = []
    for event in _rows(manager, 'LegislativeVoteEvent'):
        if getattr(event, 'legislation_name', '') \
                != legislation_name:
            continue
        roster = json.loads(event.votes_json or '{}')
        declared = json.loads(event.vote_counts_json or '{}')
        tallied = {choice: 0 for choice in VOTE_CHOICES}
        for choice in roster.values():
            tallied[choice] = tallied.get(choice, 0) + 1
        entry = {'voteEvent': event.name,
                 'chamber': event.chamber,
                 'occurredAt': event.occurred_at,
                 'result': event.result, 'roster': roster,
                 'declaredCounts': declared,
                 'rosterTallies': tallied}
        drift = {choice: (declared.get(choice, 0),
                          tallied.get(choice, 0))
                 for choice in set(declared) | set(tallied)
                 if declared.get(choice, 0)
                 != tallied.get(choice, 0)}
        if drift:
            entry['warning'] = (
                f'declared counts disagree with the roster tallies '
                f'({ {c: f"declared {d} vs roster {t}" for c, (d, t) in drift.items()} }) '
                f'— verify the source record')
        events.append(entry)
    if not events:
        return {'ok': False,
                'error': f'no vote events recorded for '
                         f"'{legislation_name}'",
                'suggestion': {
                    'knob': 'LegislativeVoteEvent',
                    'action': 'enter the vote via '
                              'enter_vote_event (manual) or an '
                              'official-API pull'}}
    return {'ok': True, 'legislation': legislation_name,
            'voteEvents': events}


def contributions_for(manager, legislation_name):
    """Per-provision contributor breakdown — what lobbies or other
    groups contributed which parts."""
    if _by_name(manager, 'LegislationRecord').get(
            legislation_name) is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    provisions = []
    for provision in _rows(manager, 'LegislationProvision'):
        if getattr(provision, 'legislation_name', '') \
                != legislation_name:
            continue
        provisions.append({
            'provision': provision.name,
            'sectionRef': provision.section_ref,
            'issue': provision.issue_name,
            'contributedBy': json.loads(
                provision.contributed_by_json or '[]'),
            'addedAt': provision.added_at or None})
    return {'ok': True, 'legislation': legislation_name,
            'provisions': provisions}


def legislator_voting_record(manager, legislator_subject):
    """One legislator's yes/no history across every recorded vote."""
    record = []
    for event in sorted(_rows(manager, 'LegislativeVoteEvent'),
                        key=lambda e: getattr(e, 'occurred_at', '')):
        roster = json.loads(getattr(event, 'votes_json', '{}')
                            or '{}')
        if legislator_subject in roster:
            record.append({'voteEvent': event.name,
                           'legislation': event.legislation_name,
                           'occurredAt': event.occurred_at,
                           'vote': roster[legislator_subject]})
    if not record:
        return {'ok': False,
                'error': f'no recorded votes for '
                         f'{legislator_subject!r}',
                'suggestion': {
                    'knob': 'LegislativeVoteEvent.votes_json',
                    'action': 'roster keys must match the '
                              'ScoreSubject name exactly'}}
    return {'ok': True, 'legislator': legislator_subject,
            'votes': record,
            'tallies': {choice: sum(1 for r in record
                                    if r['vote'] == choice)
                        for choice in VOTE_CHOICES}}


# --- burial-pattern detection ---------------------------------------

_STOP = {'the', 'a', 'an', 'of', 'for', 'and', 'or', 'to', 'in',
         'on', 'act', 'bill', 'rules'}


def _topic_tokens(text):
    tokens = set()
    for raw in (text or '').lower().replace('-', ' ').split():
        token = raw.strip('.,;:()')
        if token and token not in _STOP:
            # crude suffix folding, matching abstraction.py's spirit
            for suffix in ('ing', 'es', 's'):
                if token.endswith(suffix) \
                        and len(token) > len(suffix) + 2:
                    token = token[:-len(suffix)]
                    break
            tokens.add(token)
    return tokens


def _germaneness(declared_subject, issue_name):
    declared = _topic_tokens(declared_subject)
    issue = _topic_tokens(issue_name)
    if not declared or not issue:
        return None  # honestly unassessable
    return len(declared & issue) / len(issue)


def _days_between(earlier_iso, later_iso):
    try:
        earlier = datetime.fromisoformat(earlier_iso)
        later = datetime.fromisoformat(later_iso)
    except (TypeError, ValueError):
        return None
    return (later - earlier).days


def detect_burial_patterns(manager, legislation_name,
                           last_minute_days=LAST_MINUTE_DAYS,
                           overlap_threshold=GERMANENESS_OVERLAP):
    """Findings, never verdicts: each names the sequence it matches,
    quotes the evidence, and lists the implicated parties (the
    provision's contributors + the bill's drafters)."""
    bill = _by_name(manager, 'LegislationRecord').get(
        legislation_name)
    if bill is None:
        return {'ok': False,
                'error': f'unknown legislation '
                         f'{legislation_name!r}',
                'knownLegislation': sorted(
                    _by_name(manager, 'LegislationRecord'))}
    provisions = [p for p in _rows(manager, 'LegislationProvision')
                  if getattr(p, 'legislation_name', '')
                  == legislation_name]
    if not provisions:
        return {'ok': False,
                'error': f"'{legislation_name}' has no provision "
                         f'rows to analyze',
                'suggestion': {
                    'knob': 'LegislationProvision',
                    'action': 'enter the bill parts (and their '
                              'contributors) via enter_provision'}}
    votes = [v for v in _rows(manager, 'LegislativeVoteEvent')
             if getattr(v, 'legislation_name', '')
             == legislation_name]
    drafters = json.loads(bill.drafted_by_json or '[]')
    findings = []
    for provision in provisions:
        contributors = json.loads(
            provision.contributed_by_json or '[]')
        implicated = ([{'role': 'contributor', **c}
                       for c in contributors]
                      + [{'role': 'drafter', **d}
                         for d in drafters])
        overlap = _germaneness(bill.declared_subject,
                               provision.issue_name)
        if overlap is not None and overlap <= overlap_threshold:
            findings.append({
                'pattern': 'non-germane-provision',
                'provision': provision.name,
                'sectionRef': provision.section_ref,
                'narrative': (
                    f'provision {provision.section_ref or provision.name} '
                    f"addressing '{provision.issue_name}' sits in a "
                    f"bill declared about '{bill.declared_subject}' "
                    f'(topic overlap {overlap:.2f})'),
                'evidence': {
                    'declaredSubject': bill.declared_subject,
                    'provisionIssue': provision.issue_name,
                    'topicOverlap': overlap},
                'implicated': implicated})
        if provision.added_at:
            for vote in votes:
                gap = _days_between(provision.added_at,
                                    getattr(vote, 'occurred_at', ''))
                if gap is not None and 0 <= gap <= last_minute_days:
                    findings.append({
                        'pattern': 'last-minute-insertion',
                        'provision': provision.name,
                        'sectionRef': provision.section_ref,
                        'narrative': (
                            f'provision {provision.section_ref or provision.name} '
                            f'was added {gap} day(s) before the '
                            f'{vote.chamber or "floor"} vote of '
                            f'{vote.occurred_at}'),
                        'evidence': {
                            'addedAt': provision.added_at,
                            'voteAt': vote.occurred_at,
                            'gapDays': gap,
                            'voteEvent': vote.name},
                        'implicated': implicated})
                    break
    return {'ok': True, 'legislation': legislation_name,
            'findings': findings,
            'note': 'findings state that a recorded sequence '
                    'matches a pattern — they are evidence for '
                    'assertions, not verdicts'}


def file_burial_assertion(manager, finding, asserted_by):
    """One finding -> one REAL scr-6 ScoreAssertion, status
    'asserted' (validity votes adjudicate — never the detector)."""
    if not isinstance(finding, dict) or 'pattern' not in finding:
        return {'ok': False,
                'error': 'finding must be a detect_burial_patterns '
                         'entry'}
    implicated = finding.get('implicated') or []
    subject = next((entry['name'] for entry in implicated
                    if entry.get('kind') == 'legislator'), '')
    name = (f"assert-{finding['pattern']}-"
            f"{finding.get('provision', 'unknown')}")
    if _by_name(manager, 'ScoreAssertion').get(name) is not None:
        return {'ok': False,
                'error': f"assertion '{name}' already filed"}
    row = ScoreAssertion(
        name=name,
        display_name=f"{finding['pattern']}: "
                     f"{finding.get('sectionRef') or finding.get('provision')}",
        subject_name=subject,
        target_ref_json=json.dumps(
            {'provision': finding.get('provision')}),
        intent=finding.get('narrative', ''),
        assertion_type='score-impact', direction='harms',
        strength=0.5,
        evidence_names_json='[]',
        asserted_by=asserted_by, status='asserted',
        provenance_id='scoring.legislation.detect_burial_patterns '
                      '(pattern match + recorded rows)',
        notes=json.dumps(finding.get('evidence', {})),
        manager=manager)
    _insert(manager, 'ScoreAssertion', row)
    return {'ok': True, 'assertion': name, 'status': 'asserted',
            'subject': subject or None,
            'implicated': implicated,
            'note': 'asserted, not confirmed — validity votes '
                    'adjudicate'}
