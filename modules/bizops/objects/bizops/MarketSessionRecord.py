"""
@module bizops.objects.bizops.MarketSessionRecord

Row class MarketSessionRecord of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MarketSessionRecord(treeObject):
    """One market/online selling session — the stage-0
    FEEDBACK loop: what was offered, what actually sold, for how
    much. Sell-through per variant is what turns speculative
    batches into informed ones."""

    @treeObjectInit
    def __init__(self, name='', business_ref='', channel='',
                 session_note='', offered_json='{}', sold_json='{}',
                 revenue_usd=0.0, is_prior=False,
                 provenance_id='biz-1', notes='', manager=None):
        self.name = name
        self.business_ref = business_ref
        #: farmer-market | maker-market | online.
        self.channel = channel
        self.session_note = session_note
        #: JSON {variant: unitsOffered}.
        self.offered_json = offered_json
        #: JSON {variant: unitsSold}.
        self.sold_json = sold_json
        self.revenue_usd = revenue_usd
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
