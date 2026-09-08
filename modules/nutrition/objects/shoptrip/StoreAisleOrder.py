"""
@module nutrition.objects.shoptrip.StoreAisleOrder

Row class StoreAisleOrder of the nutrition module — one class per file (design §7), split
from shoptrip_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StoreAisleOrder(treeObject):
    """The order one store's aisles are walked — a per-store knob."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-grocery-order').
        name: str = '',
        # SourceLocation.name this order belongs to.
        location_name: str = '',
        # household that walks it this way ('' = shared/global).
        household_name: str = '',
        # JSON ordered list of aisle category labels.
        aisle_order_json: str = '[]',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.location_name = location_name
        self.household_name = household_name
        self.aisle_order_json = aisle_order_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
