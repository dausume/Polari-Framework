"""
@module supplychain.objects.sourcing.ProductFormula

Row class ProductFormula of the supplychain module — one class per file (design §7), split
from sourcing_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProductFormula(treeObject):
    """One CONCRETE blend of a product: component item_refs with
    mass fractions, each filling a requirement role. Costing turns
    this into USD/kg via the citations — the material-cost-per-kg
    scoring term for simulation results."""

    @treeObjectInit
    def __init__(self, name='', display_name='', product_item_ref='',
                 components_json='[]', yield_fraction=1.0,
                 status='candidate', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: JSON list of {item_ref, role, fraction} — mass fractions
        #: that must satisfy the product's ProductInputRequirement.
        self.components_json = components_json
        #: kg of PRODUCT per kg of input blend (1.0 = casting-like;
        #: <1 = mass leaves during processing, e.g. sol-gel drying).
        #: Costing divides by this so usdPerKg is OUTPUT basis.
        self.yield_fraction = yield_fraction
        self.status = status
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
