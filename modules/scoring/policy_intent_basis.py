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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/policy_intent/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.policy_intent._shared import WHO_MAY_SET, _by_name, _drafters_of, _persist, _rows, current_intent, intent_chain, intent_suggestions  # noqa: F401
from scoring.objects.policy_intent.PolicyIntent import PolicyIntent  # noqa: F401

from datetime import datetime, timezone
import json

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
