"""@module scoring.objects.policy_intent._shared — what the policy_intent row classes share (constants, seeds, helpers); split from policy_intent_basis.py (sap-2c)."""
from types import SimpleNamespace
import json

WHO_MAY_SET = ('the drafters themselves, if they choose to '
               'personally participate in the process')
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
def _drafters_of(draft):
    """Every identity allowed to set intent: the draft's drafted_by,
    plus any names in a drafted_by_json list when the row carries
    one (LegislationRecord-style multi-author drafts)."""
    drafters = set()
    single = getattr(draft, 'drafted_by', '')
    if single:
        drafters.add(single)
    raw = getattr(draft, 'drafted_by_json', '') or '[]'
    try:
        for entry in json.loads(raw):
            if isinstance(entry, dict) and entry.get('name'):
                drafters.add(entry['name'])
            elif isinstance(entry, str) and entry:
                drafters.add(entry)
    except Exception:
        pass
    return drafters
def intent_chain(manager, draft_name):
    """Every intent ever set for a draft, oldest first."""
    return sorted(
        (i for i in _rows(manager, 'PolicyIntent')
         if getattr(i, 'draft_name', '') == draft_name),
        key=lambda i: getattr(i, 'set_at', ''))
def current_intent(manager, draft_name):
    """The draft's current intent (+ chain length), or an honest
    'none set' with the participation framing."""
    draft = _by_name(manager, 'PolicyDraft', draft_name)
    if draft is None:
        known = sorted(getattr(d, 'name', '')
                       for d in _rows(manager, 'PolicyDraft'))
        return {'ok': False,
                'error': f"no PolicyDraft named '{draft_name}'",
                'knownDrafts': known}
    chain = intent_chain(manager, draft_name)
    current = next((i for i in chain
                    if not getattr(i, 'superseded_by', '')), None)
    if current is None:
        return {'ok': True, 'intent': None,
                'chainLength': len(chain),
                'note': 'no intent set — participation is the '
                        f"drafter's choice ({WHO_MAY_SET})"}
    return {'ok': True, 'intent': getattr(current, 'name', ''),
            'intentText': getattr(current, 'intent_text', ''),
            'expectedOutcomes': json.loads(
                getattr(current, 'expected_outcomes_json', '')
                or '[]'),
            'setBy': getattr(current, 'set_by', ''),
            'setAt': getattr(current, 'set_at', ''),
            'chainLength': len(chain)}
def intent_suggestions(manager, intent_name):
    """Feed the drafter's intent text through the REAL scr-5
    matcher (suggest_scores_for_assertion) via a transient probe row
    — the drafter's own words yield suggested term/concept bindings,
    never auto-bound."""
    from scoring.custom.abstraction import suggest_scores_for_assertion
    intent = _by_name(manager, 'PolicyIntent', intent_name)
    if intent is None:
        known = sorted(getattr(i, 'name', '')
                       for i in _rows(manager, 'PolicyIntent'))
        return {'ok': False,
                'error': f"no PolicyIntent named '{intent_name}'",
                'knownIntents': known}
    probe_name = f'intent-probe--{intent_name}'
    probe = SimpleNamespace(name=probe_name,
                            intent=getattr(intent, 'intent_text', ''))
    table = manager.objectTables.setdefault('ScoreAssertion', {})
    table[probe_name] = probe
    try:
        result = suggest_scores_for_assertion(manager, probe_name)
    finally:
        table.pop(probe_name, None)
    if not result.get('ok'):
        return result
    result['intent'] = intent_name
    result['draft'] = getattr(intent, 'draft_name', '')
    result['note'] = ('suggestions from the drafter-stated intent — '
                      'bindings stay knobs, never auto-applied')
    return result
