"""
@module supplychain.objects.sourcing.ProductInputRequirement

Row class ProductInputRequirement of the supplychain module — one class per file (design §7), split
from sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProductInputRequirement(treeObject):
    """THE FULL required-input map for one product: every role the
    product needs filled, with fraction ranges and ALL candidate
    item_refs per role — cited or not (uncited candidates are the
    research gaps, listed not hidden). This is what lets a formula
    search know its complete feedstock space."""

    @treeObjectInit
    def __init__(self, name='', display_name='', product_item_ref='',
                 roles_json='[]', substitutes_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: JSON list of {role, purpose, min_fraction, max_fraction,
        #: candidates: [item_ref, ...]} — fractions by mass.
        self.roles_json = roles_json
        #: JSON list of {item_ref, caveats: [...], notes} — WHOLE-
        #: product substitutes (not role candidates): things that can
        #: stand in for the finished product, caveats stated as data
        #: (e.g. contains plastics / fume emission) so cost
        #: comparisons never hide what the cheaper option costs you.
        self.substitutes_json = substitutes_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
