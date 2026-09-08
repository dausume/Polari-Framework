"""@module scoring.objects.legislation._shared — what the legislation row classes share (constants, seeds, helpers); split from legislation_basis.py (sap-2c)."""
from scoring.assertions_basis import ScoreAssertion
from scoring.worldview_elections_basis import _by_name, _rows
from datetime import datetime
import json

LEGISLATION_STATUSES = ('introduced', 'in-committee', 'passed',
                        'enacted', 'vetoed', 'failed')
KNOWN_LEGISLATURES = ('us-house', 'us-senate', 'dc-council',
                      'va-general-assembly', 'md-general-assembly')
CONTRIBUTOR_KINDS = ('legislator', 'staff', 'lobby', 'group',
                     'individual')
VOTE_CHOICES = ('yes', 'no', 'abstain', 'absent')
ENTRY_MODES = ('api', 'manual')
LAST_MINUTE_DAYS = 3
GERMANENESS_OVERLAP = 0.2
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
        provenance_id='scoring.legislation_basis.detect_burial_patterns '
                      '(pattern match + recorded rows)',
        notes=json.dumps(finding.get('evidence', {})),
        manager=manager)
    _insert(manager, 'ScoreAssertion', row)
    return {'ok': True, 'assertion': name, 'status': 'asserted',
            'subject': subject or None,
            'implicated': implicated,
            'note': 'asserted, not confirmed — validity votes '
                    'adjudicate'}
