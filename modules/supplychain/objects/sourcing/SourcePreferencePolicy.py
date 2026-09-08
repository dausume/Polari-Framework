"""
@module supplychain.objects.sourcing.SourcePreferencePolicy

Row class SourcePreferencePolicy of the supplychain module — one class per file (design §7), split
from sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SourcePreferencePolicy(treeObject):
    """The DEFINABLE ladder: ordered rules, each a predicate over the
    source flags; first match wins; unmatched sources get
    default_rank. Policies are rows — edit the ladder, not code."""

    @treeObjectInit
    def __init__(self, name='', display_name='', rules_json='[]',
                 default_rank=99, is_active=True, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: JSON list of {rank, label, require: {flag: bool, ...},
        #: availability?: [...]} — evaluated in order.
        self.rules_json = rules_json
        self.default_rank = default_rank
        self.is_active = is_active
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
