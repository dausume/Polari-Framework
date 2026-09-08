"""
@module scoring.objects.term_competition.TermRelationAssertion

Row class TermRelationAssertion of the scoring module — one class per file (design §7), split
from term_competition_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TermRelationAssertion(treeObject):
    """One asserted logical relation between two terms."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        subject_term: str = '',
        related_term: str = '',
        # RELATION_KINDS entry. 'logical-subset' means related_term
        # is INCORPORATED INTO subject_term.
        relation: str = '',
        asserted_by: str = '',
        on_behalf_of_group: str = '',
        rationale: str = '',
        evidence_url: str = '',
        # RELATION_STATUSES entry + append-only history.
        status: str = 'asserted',
        status_history_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_term = subject_term
        self.related_term = related_term
        self.relation = relation
        self.asserted_by = asserted_by
        self.on_behalf_of_group = on_behalf_of_group
        self.rationale = rationale
        self.evidence_url = evidence_url
        self.status = status
        self.status_history_json = status_history_json
        self.notes = notes
