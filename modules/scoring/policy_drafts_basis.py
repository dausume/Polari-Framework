"""
@cross-cutting
@module scoring.policy_drafts_basis
@tags @xc:bindings

Policy DRAFTS as first-class scoreable subjects (Dustin 2026-07-16:
"make sure the functionality for asserting scores and concepts to
policies that exist and policy drafts for developing policies is
possible"). Existing policies are already ScoreSubjects (kind
'policy', bound by ScoreAssertions/ScoreConcepts); this module gives
DEVELOPING policies the same treatment:

  * `PolicyDraft` rows carry the draft's lifecycle (a validated
    transition table + append-only history, the assertions.py
    tamper-evidence idiom).
  * `ensure_draft_subject` mints ONE ScoreSubject (kind
    'policy-draft', object_ref_json anchored to the draft row —
    object-coherence) so the UNCHANGED assertion/concept machinery
    binds to drafts exactly as it binds to enacted policies.
  * `enact_draft` links the draft to the real policy subject on
    enactment. ScoreSubject has no equivalence field (checked), so
    carryover is an explicit, honest read: `draft_score_carryover`
    returns every draft-era assertion/value annotated for the
    enacted policy — the reader sees the draft history travel, and
    nothing is silently rewritten onto the policy subject.

@consumers
  - scoring.venue_patterns_basis (policy_ref may name a draft)
  - polariServer.defClassList (auto-CRUDE + persistence)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/policy_drafts/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.scoring_basis import ScoreSubject
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.policy_drafts._shared import DRAFT_STATUSES, DRAFT_SUBJECT_KIND, DRAFT_TRANSITIONS, _persist, _register, draft_score_carryover, draft_subject_name, enact_draft, ensure_draft_subject, transition_draft  # noqa: F401
from scoring.objects.policy_drafts.PolicyDraft import PolicyDraft  # noqa: F401

from scoring.worldview_elections_basis import _by_name, _rows

def create_draft(manager, name, display_name='', description='',
                 drafted_by='', sponsoring_group='',
                 jurisdiction_subject_name='', text_url='',
                 notes=''):
    if not isinstance(name, str) or not name:
        return {'ok': False,
                'error': 'draft name must be a non-empty string'}
    if _by_name(manager, 'PolicyDraft').get(name) is not None:
        return {'ok': False,
                'error': f"a PolicyDraft named '{name}' already "
                         f'exists'}
    draft = PolicyDraft(
        name=name, display_name=display_name or name,
        description=description, status='draft',
        drafted_by=drafted_by, sponsoring_group=sponsoring_group,
        jurisdiction_subject_name=jurisdiction_subject_name,
        text_url=text_url, history_json='[]', notes=notes,
        manager=manager)
    _register(manager, 'PolicyDraft', draft)
    return {'ok': True, 'draft': name, 'status': draft.status}
