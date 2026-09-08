"""
@module scoring.objects.term_competition.TermProposal

Row class TermProposal of the scoring module — one class per file (design §7), split
from term_competition_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TermProposal(treeObject):
    """One group's composite/computed term, in consideration for one
    Score (concept)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('quality-adjusted-rent--housing-price-tenants').
        name: str = '',
        # The ScoreTerm being proposed (new or existing row).
        proposed_term_name: str = '',
        # The Score under consideration.
        for_concept_name: str = '',
        proposed_by_group: str = '',
        proposed_by: str = '',
        # How the term is computed, every entry CITED:
        # [{"sourceTerm"|"sourceName": ..., "operation": ...,
        #   "source_name": <registered source>, "citation_url": ...,
        #   "note": ...}, ...]
        composition_json: str = '[]',
        rationale: str = '',
        # PROPOSAL_STATUSES entry.
        status: str = 'proposed',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.proposed_term_name = proposed_term_name
        self.for_concept_name = for_concept_name
        self.proposed_by_group = proposed_by_group
        self.proposed_by = proposed_by
        self.composition_json = composition_json
        self.rationale = rationale
        self.status = status
        self.notes = notes
