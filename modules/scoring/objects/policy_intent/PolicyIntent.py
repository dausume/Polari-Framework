"""
@module scoring.objects.policy_intent.PolicyIntent

Row class PolicyIntent of the scoring module — one class per file (design §7), split
from policy_intent_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
