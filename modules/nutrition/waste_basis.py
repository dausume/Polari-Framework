"""
@cross-cutting
@module nutrition.waste_basis
@tags @xc:bindings

mpb-4 (waste half) — the waste ledger: food that left the kitchen
uneaten is usually the biggest hidden budget leak, so it gets its
own facts:

  WasteRecord   one discarded lot: household × food × amount ×
                REASON × date. The $ value is DERIVED at read time
                from the best observed price (labeled estimate) —
                never stored, so a price correction re-prices past
                waste honestly.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.waste_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-4
"""

from objectTreeDecorators import treeObject, treeObjectInit

WASTE_REASONS = ('spoiled', 'expired', 'plate-waste',
                 'over-prepped', 'other')

_PROV = 'mpb-4 (MEAL_PLANNING_APP_PLAN §3b)'


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


#: One demo row so the report renders.
SEED_WASTE_RECORDS = [
    {'name': 'demo-waste-spinach', 'household_name':
     'demo-household', 'food_name': 'spinach-raw',
     'quantity': 0.5, 'unit': 'bunch', 'reason': 'spoiled',
     'date': '2026-08-30', 'pantry_item_name': '',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo row — log real waste, it is the honest '
              'budget leak'},
]
