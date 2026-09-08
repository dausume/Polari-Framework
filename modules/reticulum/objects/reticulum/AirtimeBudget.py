"""
@module reticulum.objects.reticulum.AirtimeBudget

Row class AirtimeBudget of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AirtimeBudget(treeObject):
    """Duty-cycle accounting per interface — the netledger analogue
    for spectrum. In some bands the budget is 1%; it is a hard budget,
    not a guideline, so it is LEDGERED."""

    @treeObjectInit
    def __init__(self, name='', interface_name='', window_seconds=3600,
                 budget_ms=0, consumed_ms=0, duty_cycle_pct=0.0,
                 window_started_ms=0, notes='', manager=None):
        self.name = name
        self.interface_name = interface_name
        self.window_seconds = window_seconds
        self.budget_ms = budget_ms
        self.consumed_ms = consumed_ms
        self.duty_cycle_pct = duty_cycle_pct
        self.window_started_ms = window_started_ms
        self.notes = notes
