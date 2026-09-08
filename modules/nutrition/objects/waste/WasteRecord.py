"""
@module nutrition.objects.waste.WasteRecord

Row class WasteRecord of the nutrition module — one class per file (design §7), split
from waste_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WasteRecord(treeObject):
    """One discarded lot of food (a fact with a reason)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-household-spinach-2026-08-30').
        name: str = '',
        household_name: str = '',
        food_name: str = '',
        quantity: float = 0.0,
        # any unit the weight priors resolve.
        unit: str = 'g',
        # WASTE_REASONS entry.
        reason: str = 'spoiled',
        # ISO date discarded.
        date: str = '',
        # the PantryItem it came from ('' = untracked lot).
        pantry_item_name: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.household_name = household_name
        self.food_name = food_name
        self.quantity = quantity
        self.unit = unit
        self.reason = reason
        self.date = date
        self.pantry_item_name = pantry_item_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
