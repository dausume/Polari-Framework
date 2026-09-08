"""
@cross-cutting
@module scoring.policy_intent_basis
@tags @xc:bindings

Drafter-set PolicyIntent (Dustin 2026-07-16): "the policy drafters
themselves to set their own PolicyIntent, if they choose to
personally participate in the process."

An intent is the DRAFTER'S OWN statement of what the draft is meant
to do — voluntary, first-person participation. Only the draft's
drafters may set one (refusals name that rule verbatim). Intents are
append-only: a new intent supersedes the previous via a pointer, and
the full chain stays readable — a drafter can refine their stated
intent, never silently rewrite it.

The stated intent feeds the scr-5 abstraction matcher (the REAL
suggest_scores_for_assertion, via a transient probe row) so the
drafter's own words yield SUGGESTED term/concept bindings for the
draft's eventual scoring — knobs-and-suggestions, never auto-bound.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.policy_drafts_basis (drafts these intents attach to)
@see /OVERLAP_MAP.md
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from objectTreeDecorators import treeObject, treeObjectInit

WHO_MAY_SET = ('the drafters themselves, if they choose to '
               'personally participate in the process')


class PolicyIntent(treeObject):
    """One drafter-stated intent for one PolicyDraft. Content is
    immutable; a newer intent points at nothing and the older one
    gains superseded_by — the chain is the history."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('intent-<draft>-2').
        name: str = '',
        draft_name: str = '',
        # Contributor — must be one of the draft's drafters.
        set_by: str = '',
        # The generic intent statement, the drafter's own words.
        intent_text: str = '',
        # JSON list of plain expected-outcome statements.
        expected_outcomes_json: str = '[]',
        set_at: str = '',
        # '' = current; else the name of the intent that replaced
        # this one (append-only supersede chain).
        superseded_by: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.draft_name = draft_name
        self.set_by = set_by
        self.intent_text = intent_text
        self.expected_outcomes_json = expected_outcomes_json
        self.set_at = set_at
        self.superseded_by = superseded_by
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


def set_policy_intent(manager, draft_name, set_by, intent_text,
                      expected_outcomes=None, set_at='', notes=''):
    """The drafter's voluntary act: state (or restate) the intent.
    Non-drafters are refused — intent-setting belongs to
    WHO_MAY_SET."""
    draft = _by_name(manager, 'PolicyDraft', draft_name)
    if draft is None:
        known = sorted(getattr(d, 'name', '')
                       for d in _rows(manager, 'PolicyDraft'))
        return {'ok': False,
                'error': f"no PolicyDraft named '{draft_name}'",
                'knownDrafts': known}
    drafters = _drafters_of(draft)
    if not set_by or set_by not in drafters:
        return {'ok': False,
                'error': f"'{set_by}' is not a drafter of "
                         f"'{draft_name}' — intent may be set only "
                         f'by {WHO_MAY_SET}',
                'drafters': sorted(drafters)}
    if not (intent_text or '').strip():
        return {'ok': False,
                'error': 'intent_text is required — the intent IS '
                         "the drafter's statement"}
    chain = intent_chain(manager, draft_name)
    current = next((i for i in chain
                    if not getattr(i, 'superseded_by', '')), None)
    name = f'intent-{draft_name}-{len(chain) + 1}'
    if _by_name(manager, 'PolicyIntent', name) is not None:
        return {'ok': False,
                'error': f"an intent named '{name}' already exists"}
    set_at = set_at or datetime.now(timezone.utc).isoformat(
        timespec='seconds')
    intent = PolicyIntent(
        name=name, draft_name=draft_name, set_by=set_by,
        intent_text=intent_text,
        expected_outcomes_json=json.dumps(
            list(expected_outcomes or [])),
        set_at=set_at, notes=notes, manager=manager)
    table = manager.objectTables.setdefault('PolicyIntent', {})
    if not any(existing is intent for existing in table.values()):
        table[name] = intent
    if current is not None:
        current.superseded_by = name
        _persist(manager, current)
    _persist(manager, intent)
    return {'ok': True, 'intent': name,
            'supersedes': getattr(current, 'name', None)
            if current is not None else None,
            'setBy': set_by, 'setAt': set_at}


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
