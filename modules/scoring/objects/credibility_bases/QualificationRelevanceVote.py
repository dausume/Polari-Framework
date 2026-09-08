"""
@module scoring.objects.credibility_bases.QualificationRelevanceVote

Row class QualificationRelevanceVote of the scoring module — one class per file (design §7), split
from credibility_bases_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class QualificationRelevanceVote(treeObject):
    """One unit's vote on whether a basis kind (or a kind:qualifier)
    is RELEVANT for a given context/concept — 'so that people can
    more quickly see and give priority to those inputs without being
    drowned out'. Ranking input only: relevance ORDERS readings, it
    never excludes anyone."""

    @treeObjectInit
    def __init__(self, name: str = '', context_name: str = '',
                 basis_kind: str = '', qualifier: str = '',
                 voter: str = '', on_behalf_of_group: str = '',
                 relevant: bool = True, rationale: str = '',
                 cast_at: str = '', notes: str = '', manager=None):
        self.name = name
        self.context_name = context_name
        self.basis_kind = basis_kind
        self.qualifier = qualifier
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.relevant = relevant
        self.rationale = rationale
        self.cast_at = cast_at
        self.notes = notes
