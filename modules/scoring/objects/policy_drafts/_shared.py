"""@module scoring.objects.policy_drafts._shared — what the policy_drafts row classes share (constants, seeds, helpers); split from policy_drafts_basis.py (sap-2c)."""
from scoring.scoring_basis import ScoreSubject
from scoring.worldview_elections_basis import _by_name, _rows
from datetime import datetime, timezone
import json

DRAFT_STATUSES = ('draft', 'introduced', 'in-committee', 'passed',
                  'enacted', 'failed', 'withdrawn')
DRAFT_TRANSITIONS = {
    'draft': ('introduced', 'withdrawn'),
    'introduced': ('in-committee', 'passed', 'failed', 'withdrawn'),
    'in-committee': ('passed', 'failed', 'withdrawn'),
    'passed': ('enacted', 'failed'),
    'enacted': (),
    'failed': ('introduced',),
    'withdrawn': (),
}
DRAFT_SUBJECT_KIND = 'policy-draft'
def _persist(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
def _register(manager, table_name, row):
    table = manager.objectTables.setdefault(table_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row
def transition_draft(manager, name, to_status, by='', note=''):
    """Move a draft through its lifecycle — validated against
    DRAFT_TRANSITIONS, every move appended to history_json."""
    draft = _by_name(manager, 'PolicyDraft').get(name)
    if draft is None:
        return {'ok': False,
                'error': f"no PolicyDraft named '{name}'",
                'knownDrafts': sorted(_by_name(manager,
                                               'PolicyDraft'))}
    if to_status not in DRAFT_STATUSES:
        return {'ok': False,
                'error': f"unknown status '{to_status}'",
                'statuses': list(DRAFT_STATUSES)}
    allowed = DRAFT_TRANSITIONS.get(draft.status, ())
    if to_status not in allowed:
        return {'ok': False,
                'error': f"'{draft.status}' cannot transition to "
                         f"'{to_status}'",
                'allowed': list(allowed)}
    history = json.loads(draft.history_json or '[]')
    history.append({'from': draft.status, 'to': to_status, 'by': by,
                    'note': note,
                    'at': datetime.now(timezone.utc).isoformat()})
    draft.history_json = json.dumps(history)
    draft.status = to_status
    _persist(manager, draft)
    return {'ok': True, 'draft': name, 'status': to_status,
            'historyLength': len(history)}
def draft_subject_name(draft_name):
    return f'draft--{draft_name}'
def ensure_draft_subject(manager, draft_name):
    """The key capability: a ScoreSubject for the draft, so the
    UNCHANGED assertion/concept machinery binds to it. Idempotent."""
    draft = _by_name(manager, 'PolicyDraft').get(draft_name)
    if draft is None:
        return {'ok': False,
                'error': f"no PolicyDraft named '{draft_name}'",
                'knownDrafts': sorted(_by_name(manager,
                                               'PolicyDraft'))}
    subject_name = draft_subject_name(draft_name)
    existing = _by_name(manager, 'ScoreSubject').get(subject_name)
    if existing is not None:
        return {'ok': True, 'subject': subject_name,
                'created': False}
    subject = ScoreSubject(
        name=subject_name,
        display_name=f'{draft.display_name} (draft)',
        kind=DRAFT_SUBJECT_KIND,
        object_ref_json=json.dumps({'kind': 'objectRef',
                                    'className': 'PolicyDraft',
                                    'name': draft_name}),
        description=f'scoreable subject for developing policy '
                    f"'{draft_name}' — assertions and concepts bind "
                    f'here before enactment',
        manager=manager)
    _register(manager, 'ScoreSubject', subject)
    return {'ok': True, 'subject': subject_name, 'created': True}
def enact_draft(manager, draft_name, policy_subject_name, by='',
                note=''):
    """passed -> enacted + the link to the real policy subject."""
    policy = _by_name(manager, 'ScoreSubject').get(
        policy_subject_name)
    if policy is None:
        return {'ok': False,
                'error': f"no ScoreSubject named "
                         f"'{policy_subject_name}' — create the "
                         f'enacted policy subject first',
                'suggestion': {
                    'knob': 'ScoreSubject',
                    'action': "add the policy row (kind 'policy') "
                              'the draft became'}}
    moved = transition_draft(manager, draft_name, 'enacted', by=by,
                             note=note or f'enacted as '
                                          f'{policy_subject_name}')
    if not moved.get('ok'):
        return moved
    draft = _by_name(manager, 'PolicyDraft').get(draft_name)
    draft.enacted_policy_subject_name = policy_subject_name
    _persist(manager, draft)
    return {'ok': True, 'draft': draft_name,
            'enactedPolicySubject': policy_subject_name,
            'carryover': 'draft-era scores stay queryable via '
                         'draft_score_carryover (explicit read — '
                         'nothing silently rewritten)'}
def draft_score_carryover(manager, draft_name):
    """Every draft-era assertion + contextualized value, annotated
    for the enacted policy. ScoreSubject has no equivalence field
    (checked), so carryover is this explicit, honest read — the
    draft history TRAVELS with the policy instead of being rewritten
    onto it."""
    draft = _by_name(manager, 'PolicyDraft').get(draft_name)
    if draft is None:
        return {'ok': False,
                'error': f"no PolicyDraft named '{draft_name}'",
                'knownDrafts': sorted(_by_name(manager,
                                               'PolicyDraft'))}
    subject = draft_subject_name(draft_name)
    assertions = [
        {'name': getattr(a, 'name', ''),
         'intent': getattr(a, 'intent', ''),
         'status': getattr(a, 'status', ''),
         'conceptName': getattr(a, 'concept_name', ''),
         'termName': getattr(a, 'term_name', '')}
        for a in _rows(manager, 'ScoreAssertion')
        if getattr(a, 'subject_name', '') == subject]
    values = [
        {'name': getattr(v, 'name', ''),
         'termName': getattr(v, 'term_name', ''),
         'value': getattr(v, 'pre_normalized_value', None)}
        for v in _rows(manager, 'ContextualizedValue')
        if getattr(v, 'subject_name', '') == subject]
    return {'ok': True, 'draft': draft_name,
            'draftSubject': subject,
            'enactedPolicySubject':
                draft.enacted_policy_subject_name or None,
            'status': draft.status,
            'assertions': assertions, 'values': values,
            'note': 'draft-era scores presented FOR the enacted '
                    'policy with their draft provenance intact'}
