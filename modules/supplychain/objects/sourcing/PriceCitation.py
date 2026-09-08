"""
@module supplychain.objects.sourcing.PriceCitation

Row class PriceCitation of the supplychain module — one class per file (design §7), split
from sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PriceCitation(treeObject):
    """One dated, cited price observation — never a bare number.
    is_estimate=True whenever the figure is inferred (a range, a
    'from' price) rather than a listed exact price."""

    @treeObjectInit
    def __init__(self, name='', source_ref='', item_ref='',
                 price=0.0, currency='USD', amount=0.0,
                 amount_unit='kg', observed_at='', citation_url='',
                 citation_note='', is_estimate=False, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.source_ref = source_ref
        self.item_ref = item_ref
        #: Price for `amount` of `amount_unit` (e.g. 109.0 for
        #: 50 lb) — normalization happens in analysis, the citation
        #: stays exactly as observed.
        self.price = price
        self.currency = currency
        self.amount = amount
        self.amount_unit = amount_unit
        #: ISO date-time of the observation.
        self.observed_at = observed_at
        self.citation_url = citation_url
        self.citation_note = citation_note
        self.is_estimate = is_estimate
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
