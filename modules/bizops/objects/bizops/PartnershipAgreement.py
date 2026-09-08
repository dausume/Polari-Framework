"""
@module bizops.objects.bizops.PartnershipAgreement

Row class PartnershipAgreement of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PartnershipAgreement(treeObject):
    """A deal between two parties (businesses and/or sources): who
    gives what to whom, on what terms. Coherence is CHECKED against
    the supply/demand rows — a deal whose flows match what the
    parties actually supply/demand is marked coherent; unresolved
    parties are honest gaps, not errors (deals can name partners
    still to be found)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', party_a='',
                 party_b='', kind='supply-deal', flows_json='[]',
                 terms_note='', status='proposed', is_prior=True,
                 provenance_id='biz-3', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: BusinessProfile or SupplySourceProfile name — or a
        #: plain-language placeholder for a partner to be found.
        self.party_a = party_a
        self.party_b = party_b
        #: supply-deal | mutual-supply | service-maintenance |
        #: capacity-share.
        self.kind = kind
        #: JSON [{from, to, item_ref, terms_note}] — the actual
        #: flows, direction explicit.
        self.flows_json = flows_json
        self.terms_note = terms_note
        #: proposed | active | ended.
        self.status = status
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
