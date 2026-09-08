"""
@module scoring.objects.group_authority.TermAvailabilitySignal

Row class TermAvailabilitySignal of the scoring module — one class per file (design §7), split
from group_authority_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TermAvailabilitySignal(treeObject):
    """One group's request that a term become available for a context
    on the PSC, adjudicated through authority_check."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('tas--<term>--<context>--<group>').
        name: str = '',
        term_name: str = '',
        context_name: str = '',
        # Optional: the Score the term is meant for.
        concept_name: str = '',
        group_name: str = '',
        instance_name: str = '',
        requested_by_subject: str = '',
        requested_by_username: str = '',
        identity_source: str = 'payload-unverified',
        # SIGNAL_STATUSES entry.
        status: str = 'pending',
        # The full authority_check verdict at decision time.
        verdict_json: str = '{}',
        created_at: str = '',
        decided_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.term_name = term_name
        self.context_name = context_name
        self.concept_name = concept_name
        self.group_name = group_name
        self.instance_name = instance_name
        self.requested_by_subject = requested_by_subject
        self.requested_by_username = requested_by_username
        self.identity_source = identity_source
        self.status = status
        self.verdict_json = verdict_json
        self.created_at = created_at
        self.decided_at = decided_at
        self.notes = notes
