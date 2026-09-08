"""
@module cntfet.objects.cnt_power.PowerBudget

Row class PowerBudget of the cntfet module — one class per file (design §7), split
from cnt_power_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PowerBudget(treeObject):
    """A power LIMIT set as a row — every limit optional (None =
    not a constraint); scope says which report it governs."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        scope: str = 'cell',          # fet | cell | block
        max_static_w: float = None,
        max_dynamic_w: float = None,
        max_density_w_per_cm2: float = None,
        max_temperature_k: float = None,
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.scope = scope
        self.max_static_w = max_static_w
        self.max_dynamic_w = max_dynamic_w
        self.max_density_w_per_cm2 = max_density_w_per_cm2
        self.max_temperature_k = max_temperature_k
        self.notes = notes
        self.is_prior = is_prior
