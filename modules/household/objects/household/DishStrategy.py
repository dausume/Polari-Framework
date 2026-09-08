"""
@module household.objects.household.DishStrategy

Row class DishStrategy of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DishStrategy(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '',
                 needs_tool: str = '', min_per_load_unit: float = 1.5,
                 setup_min: float = 2.0, cycle_min: float = 0.0, unload_min: float = 0.0,
                 timing: str = 'unattended-first',   # unattended-first | after-meal | when-full
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.needs_tool = needs_tool
        self.min_per_load_unit = min_per_load_unit
        self.setup_min = setup_min
        self.cycle_min = cycle_min
        self.unload_min = unload_min
        self.timing = timing
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
