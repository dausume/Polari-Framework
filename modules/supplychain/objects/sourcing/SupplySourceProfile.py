"""
@module supplychain.objects.sourcing.SupplySourceProfile

Row class SupplySourceProfile of the supplychain module — one class per file (design §7), split
from sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from supplychain.objects.sourcing._shared import SOURCE_AVAILABILITY

class SupplySourceProfile(treeObject):
    """One source of one-or-more items, with overlap-capable
    category flags and an availability state ('potential' = a
    business model that COULD supply this, not one that does)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', supplier_name='',
                 url='', is_open_source=False, is_commercial=False,
                 is_local=False, is_polari=False,
                 is_eco_friendly=False, availability='available',
                 supplies_json='[]', demands_json='[]',
                 business_model_ref='', locality_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.supplier_name = supplier_name
        self.url = url
        self.is_open_source = is_open_source
        self.is_commercial = is_commercial
        self.is_local = is_local
        self.is_polari = is_polari
        self.is_eco_friendly = is_eco_friendly
        self.availability = (availability
                             if availability in SOURCE_AVAILABILITY
                             else 'available')
        #: JSON list of item_refs this source supplies.
        self.supplies_json = supplies_json
        #: JSON list of item_refs the business behind this source
        #: would BUY (demand side of the loop).
        self.demands_json = demands_json
        #: BusinessModelDefinition.name (economy tree) when the
        #: source IS a modeled business (alternate-source-as-model).
        self.business_model_ref = business_model_ref
        self.locality_note = locality_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
