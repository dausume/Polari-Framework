"""
@module scoring.objects.venue_patterns.VenueActionRecord

Row class VenueActionRecord of the scoring module — one class per file (design §7), split
from venue_patterns_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VenueActionRecord(treeObject):
    """One observed action on an issue in a venue."""

    @treeObjectInit
    def __init__(self, name: str = '', issue_name: str = '',
                 # '' or a PolicyDraft/policy-subject name.
                 policy_ref: str = '',
                 venue: str = 'statute', action: str = 'introduced',
                 actor_subject_name: str = '',
                 jurisdiction_subject_name: str = '',
                 fiscal_period: str = '',
                 # ISO, caller-supplied (the observed event's date).
                 occurred_at: str = '',
                 evidence_url: str = '', provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.issue_name = issue_name
        self.policy_ref = policy_ref
        self.venue = venue
        self.action = action
        self.actor_subject_name = actor_subject_name
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.fiscal_period = fiscal_period
        self.occurred_at = occurred_at
        self.evidence_url = evidence_url
        self.provenance_id = provenance_id
        self.notes = notes
