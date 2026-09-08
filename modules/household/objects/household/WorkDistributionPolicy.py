"""
@module household.objects.household.WorkDistributionPolicy

Row class WorkDistributionPolicy of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WorkDistributionPolicy(treeObject):
    """One per workload type: how the household splits it."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 workload_type: str = 'pre-prep', mode: str = 'shares',
                 # {person_name: percent} — must sum to 100 for 'shares'.
                 shares_json: str = '{}',
                 # how far the optimiser may drift from the shares to save work.
                 share_tolerance_pct: float = 10.0,
                 assigned_person: str = '', rotation_order_json: str = '[]',
                 # delivery cost shift (mode='delivery').
                 delivery_fee: float = 0.0, delivery_markup_pct: float = 0.0,
                 delivery_min_order: float = 0.0, delivery_lead_days: int = 1,
                 # the household's OWN number ('' = compare minutes only).
                 labor_value_per_hour: str = '',
                 travel_min_per_trip: float = 0.0, travel_cost_per_trip: float = 0.0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.workload_type = workload_type
        self.mode = mode
        self.shares_json = shares_json
        self.share_tolerance_pct = share_tolerance_pct
        self.assigned_person = assigned_person
        self.rotation_order_json = rotation_order_json
        self.delivery_fee = delivery_fee
        self.delivery_markup_pct = delivery_markup_pct
        self.delivery_min_order = delivery_min_order
        self.delivery_lead_days = delivery_lead_days
        self.labor_value_per_hour = labor_value_per_hour
        self.travel_min_per_trip = travel_min_per_trip
        self.travel_cost_per_trip = travel_cost_per_trip
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
